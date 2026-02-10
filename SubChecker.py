from telethon import events, Button
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telethon.tl.functions.messages import ReportSpamRequest
from telethon.tl.types import User
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from .. import loader, utils
import asyncio
import time
from datetime import datetime, timedelta

@loader.tds
class SubCheckBot(loader.Module):
    """Буст канала от @SheoMod"""
    
    strings = {
        'name': 'SubChecker',
        'not_subscribed': "<b>Вы не подписаны на наш канал!</b>\nПожалуйста, подпишитесь на канал {channel_link}, чтобы продолжить общение.\n\n<b>В течении минуты вас разблокируют.</b>",
        'subscribed': "<b>Спасибо за подписку! Вы были разблокированы.</b>",
        'channel_not_set': "<b>Канал для проверки подписки не настроен!</b>\n\nИспользуйте команду .subchannel [юзернейм или ссылка] для настройки канала.\nПример: .subchannel @my_channel",
        'channel_set': "<b>Канал для проверки подписки установлен:</b> {}",
        'current_channel': "<b>Текущий канал для проверки:</b> {}\n\n<b>ID канала:</b> <code>{}</code>",
        'invalid_channel': "<b>Не удалось найти канал!</b>\n\nПроверьте правильность юзернейма или ссылки и убедитесь, что бот имеет доступ к каналу.",
        'test_success': "<b>Тест пройден успешно!</b>\n\nБот может получить информацию о канале и его участниках.",
        'test_failed': "<b>Тест не пройден!</b>\n\nОшибка: {}",
        'no_permission': "<b>Нет прав доступа!</b>\n\nУбедитесь, что бот является администратором канала или имеет права на просмотр участников.",
        'bot_detected': "<b>Бот обнаружен!</b>\n\nБоты не проходят проверку подписки.",
        'custom_message_set': "<b>Кастомное сообщение установлено!</b>",
        'custom_message_cleared': "<b>Кастомное сообщение сброшено!</b>",
        'current_custom_message': "<b>Текущее кастомное сообщение:</b>\n\n{}",
        'no_custom_message': "<b>Кастомное сообщение не установлено.</b>\nИспользуется стандартное сообщение.",
        'whitelist_added': "<b>Пользователь добавлен в белый список!</b>\n\nID: <code>{}</code>",
        'whitelist_removed': "<b>Пользователь удален из белого списка!</b>\n\nID: <code>{}</code>",
        'whitelist_not_found': "<b>Пользователь не найден в белом списке!</b>",
        'whitelist_empty': "<b>Белый список пуст!</b>",
        'whitelist_cleared': "<b>Белый список очищен!</b>\n\nУдалено пользователей: {}",
        'whitelist_list': "<b>Белый список пользователей:</b>\n\n{}",
        'user_in_whitelist': "<b>Пользователь в белом списке</b>\n\nID: <code>{}</code>\nДобавлен: {}",
        'user_not_in_whitelist': "<b>Пользователь не в белом списке!</b>",
        'invalid_user_id': "<b>Неверный ID пользователя!</b>\nID должен быть числом.",
        'no_reply': "<b>Ответьте на сообщение пользователя или укажите ID!</b>",
        'check_interval_set': "<b>Интервал проверки установлен:</b> {} секунд\n\nМинимальное значение: 30 секунд",
        'current_check_interval': "<b>Текущий интервал проверки:</b> {} секунд",
        'invalid_interval': "<b>Неверный интервал!</b>\n\nУкажите число секунд (минимум 30).",
        'user_blocked': "<b>Пользователь заблокирован!</b>\n\nID: <code>{}</code>\nПричина: не подписан на канал",
        'user_unblocked': "<b>Пользователь разблокирован!</b>\n\nID: <code>{}</code>\nПричина: подписался на канал",
        'blocked_users': "<b>Заблокированные пользователи:</b>\n\n{}",
        'no_blocked_users': "<b>Нет заблокированных пользователей!</b>",
        'blocked_user_info': "<b>Информация о блокировке:</b>\n\nID: <code>{}</code>\nЗаблокирован: {}\nПроверок: {}\nПоследняя проверка: {}",
        'checking_subscriptions': "<b>Запущена фоновая проверка подписок...</b>\n\nПроверяем {} пользователей",
        'check_complete': "<b>Проверка завершена!</b>\n\nПроверено: {}\nРазблокировано: {}\nВсе еще не подписаны: {}",
        'force_check_started': "<b>Принудительная проверка запущена!</b>\n\nПроверяем {} пользователей...",
        'subscribers_cache_info': "<b>Кэш подписчиков обновлен!</b>\n\nКоличество подписчиков: {}\nВремя обновления: {}",
        'cache_cleared': "<b>Кэш подписчиков очищен!</b>",
        'blocked_list_cleared': "<b>Список заблокированных пользователей очищен!</b>\n\nУдалено: {} пользователей",
    }

    def __init__(self):
        self.check_task = None
        self.check_running = False
        self.subscribers_cache = set()  # Кэш ID подписчиков
        self.last_cache_update = None
        self.cache_ttl = 300  # 5 минут TTL для кэша

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        
        # Загрузка настроек канала
        self.channel_username = self.db.get("SubChecker", "channel_username", "")
        self.channel_link = self.db.get("SubChecker", "channel_link", "")
        self.channel_id = self.db.get("SubChecker", "channel_id", None)
        
        # Загрузка сообщений о неподписке
        self.not_subscribed_msgs = self.db.get("SubChecker", "not_subscribed_msgs", {})
        
        # Загрузка кастомного сообщения
        self.custom_message = self.db.get("SubChecker", "custom_message", "")
        
        # Загрузка белого списка
        self.whitelist = self.db.get("SubChecker", "whitelist", {})
        
        # Загрузка заблокированных пользователей
        self.blocked_users = self.db.get("SubChecker", "blocked_users", {})
        
        # Интервал проверки (по умолчанию 60 секунд)
        self.check_interval = self.db.get("SubChecker", "check_interval", 60)
        if self.check_interval < 30:
            self.check_interval = 30
        
        # Включение/выключение модуля
        self.enabled = self.db.get("SubChecker", "enabled", True)
        
        # Загрузка кэша подписчиков
        cache_data = self.db.get("SubChecker", "subscribers_cache", {})
        self.subscribers_cache = set(cache_data.get('ids', []))
        self.last_cache_update = cache_data.get('last_update')
        
        # Запуск фоновой проверки
        if self.enabled and self.channel_id and not self.check_running:
            await self.start_background_checker()

    async def start_background_checker(self):
        """Запуск фоновой проверки"""
        if self.check_task and not self.check_task.done():
            return
        
        self.check_running = True
        self.check_task = asyncio.create_task(self.background_checker())

    async def stop_background_checker(self):
        """Остановка фоновой проверки"""
        self.check_running = False
        if self.check_task and not self.check_task.done():
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
        self.check_task = None

    async def update_subscribers_cache(self):
        """Обновление кэша подписчиков"""
        if not self.channel_id:
            return False
        
        try:
            print(f"Обновление кэша подписчиков для канала {self.channel_id}...")
            
            all_participants = []
            
            # Используем итератор для получения всех участников
            async for participant in self.client.iter_participants(
                self.channel_id,
                aggressive=True
            ):
                all_participants.append(participant)
                if len(all_participants) % 100 == 0:
                    await asyncio.sleep(0.5)  # Задержка чтобы не спамить
            
            # Обновляем кэш
            self.subscribers_cache = {p.id for p in all_participants}
            self.last_cache_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Сохраняем в БД
            self.db.set("SubChecker", "subscribers_cache", {
                'ids': list(self.subscribers_cache),
                'last_update': self.last_cache_update,
                'count': len(self.subscribers_cache)
            })
            
            print(f"Кэш подписчиков обновлен: {len(self.subscribers_cache)} участников")
            return True
            
        except Exception as e:
            print(f"Ошибка обновления кэша подписчиков: {e}")
            return False

    def is_cache_valid(self):
        """Проверка валидности кэша"""
        if not self.last_cache_update or not self.subscribers_cache:
            return False
        
        try:
            last_update = datetime.strptime(self.last_cache_update, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            return (now - last_update).total_seconds() < self.cache_ttl
        except:
            return False

    async def background_checker(self):
        """Фоновая проверка подписок заблокированных пользователей"""
        # Сначала обновляем кэш подписчиков
        await self.update_subscribers_cache()
        
        while self.check_running:
            try:
                if not self.enabled or not self.channel_id:
                    await asyncio.sleep(60)
                    continue
                
                # Обновляем кэш если устарел
                if not self.is_cache_valid():
                    await self.update_subscribers_cache()
                
                # Делаем копию списка для безопасной итерации
                blocked_users_copy = self.blocked_users.copy()
                
                if not blocked_users_copy:
                    await asyncio.sleep(self.check_interval)
                    continue
                
                # Проверяем каждого заблокированного пользователя
                for user_id_str in list(blocked_users_copy.keys()):
                    if not self.check_running:
                        break
                        
                    user_id = int(user_id_str)
                    
                    # Пропускаем если пользователь в белом списке
                    if self.is_whitelisted(user_id):
                        if user_id_str in self.blocked_users:
                            await self.unblock_user(user_id, "пользователь в белом списке")
                        continue
                    
                    # Проверяем подписку через кэш
                    if user_id in self.subscribers_cache:
                        # Пользователь подписался - разблокируем
                        await self.unblock_user(user_id, "подписался на канал")
                    else:
                        # Двойная проверка на случай если кэш устарел
                        try:
                            is_subscribed = await self.check_subscription_direct(user_id)
                            if is_subscribed:
                                await self.unblock_user(user_id, "подписался на канал")
                                # Обновляем кэш
                                self.subscribers_cache.add(user_id)
                        except:
                            pass
                        
                        # Обновляем счетчик проверок
                        if user_id_str in self.blocked_users:
                            self.blocked_users[user_id_str]['check_count'] = self.blocked_users[user_id_str].get('check_count', 0) + 1
                            self.blocked_users[user_id_str]['last_check'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            self.db.set("SubChecker", "blocked_users", self.blocked_users)
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Ошибка в фоновой проверке: {e}")
                await asyncio.sleep(60)

    async def block_user(self, user_id):
        """Блокировка пользователя"""
        try:
            await self.client(BlockRequest(id=user_id))
            
            # Сохраняем информацию о блокировке
            self.blocked_users[str(user_id)] = {
                'user_id': user_id,
                'blocked_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'last_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'check_count': 0,
                'reason': 'not_subscribed'
            }
            self.db.set("SubChecker", "blocked_users", self.blocked_users)
            
            return True
        except Exception as e:
            print(f"Ошибка блокировки пользователя {user_id}: {e}")
            return False

    async def unblock_user(self, user_id, reason="подписался на канал"):
        """Разблокировка пользователя"""
        try:
            await self.client(UnblockRequest(id=user_id))
            
            # Удаляем из списка заблокированных
            user_id_str = str(user_id)
            if user_id_str in self.blocked_users:
                del self.blocked_users[user_id_str]
                self.db.set("SubChecker", "blocked_users", self.blocked_users)
            
            # Удаляем сообщение о подписке если есть
            if user_id_str in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)
            
            # Отправляем сообщение о разблокировке
            try:
                await self.client.send_message(
                    user_id,
                    self.strings['subscribed']
                )
            except:
                pass
            
            print(f"Пользователь {user_id} разблокирован: {reason}")
            return True
        except Exception as e:
            print(f"Ошибка разблокировки пользователя {user_id}: {e}")
            return False

    async def check_subscription_direct(self, user_id):
        """Прямая проверка подписки пользователя на канал"""
        if not self.channel_id:
            return False
        
        try:
            # Проверяем через get_participants с фильтром по ID
            participants = await self.client.get_participants(
                self.channel_id,
                filter=User(id=user_id),
                limit=1
            )
            
            return len(participants) > 0 and participants[0].id == user_id
        except:
            # Альтернативный метод - итерация
            try:
                async for participant in self.client.iter_participants(
                    self.channel_id,
                    search=str(user_id),
                    limit=10
                ):
                    if participant.id == user_id:
                        return True
                    await asyncio.sleep(0.01)
            except:
                pass
            
            return False

    async def check_subscription(self, user_id):
        """Оптимизированная проверка подписки пользователя на канал"""
        if not self.channel_id:
            return False
        
        # Сначала проверяем кэш
        if user_id in self.subscribers_cache:
            return True
        
        # Если кэш невалиден, обновляем его
        if not self.is_cache_valid():
            await self.update_subscribers_cache()
            return user_id in self.subscribers_cache
        
        # Двойная проверка на случай если пользователь недавно подписался
        return await self.check_subscription_direct(user_id)

    def is_bot(self, user):
        """Проверка, является ли пользователь ботом"""
        if isinstance(user, User):
            return user.bot
        return False

    def is_whitelisted(self, user_id):
        """Проверка, находится ли пользователь в белом списке"""
        return str(user_id) in self.whitelist

    def add_to_whitelist(self, user_id, added_by=None):
        """Добавление пользователя в белый список"""
        self.whitelist[str(user_id)] = {
            'added_by': added_by,
            'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_id': user_id
        }
        self.db.set("SubChecker", "whitelist", self.whitelist)
        
        # Если пользователь был заблокирован - разблокируем
        if str(user_id) in self.blocked_users:
            asyncio.create_task(self.unblock_user(user_id, "добавлен в белый список"))

    def remove_from_whitelist(self, user_id):
        """Удаление пользователя из белого списка"""
        if str(user_id) in self.whitelist:
            del self.whitelist[str(user_id)]
            self.db.set("SubChecker", "whitelist", self.whitelist)
            return True
        return False

    async def save_not_subscribed_msg(self, user_id, message_id):
        """Сохранение ID сообщения о неподписке"""
        self.not_subscribed_msgs[str(user_id)] = message_id
        self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)

    async def delete_not_subscribed_msg(self, user_id):
        """Удаление сообщения о неподписке"""
        if str(user_id) in self.not_subscribed_msgs:
            try:
                await self.client.delete_messages(user_id, self.not_subscribed_msgs[str(user_id)])
            except:
                pass
            del self.not_subscribed_msgs[str(user_id)]
            self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)

    def get_not_subscribed_message(self):
        """Получение сообщения о неподписке"""
        if self.custom_message:
            if self.channel_link:
                channel_display = f'<a href="{self.channel_link}">{self.channel_username or "наш канал"}</a>'
            else:
                channel_display = self.channel_username or "наш канал"
            return self.custom_message.replace("{channel_link}", channel_display)
        
        if self.channel_link:
            channel_display = f'<a href="{self.channel_link}">{self.channel_username or "наш канал"}</a>'
        else:
            channel_display = self.channel_username or "наш канал"
        
        return self.strings['not_subscribed'].format(channel_link=channel_display)

    @loader.command()
    async def subwl(self, message):
        """Управление белым списком"""
        args = utils.get_args_raw(message)
        
        if not args:
            # Показать статус белого списка
            total_users = len(self.whitelist)
            status = f"<b>Белый список:</b> {total_users} пользователей\n\n"
            status += "<b>Команды:</b>\n"
            status += ".subwl add [ID] - добавить пользователя\n"
            status += ".subwl remove [ID] - удалить пользователя\n"
            status += ".subwl list - показать список\n"
            status += ".subwl clear - очистить список\n"
            status += ".subwl check [ID] - проверить пользователя\n"
            await utils.answer(message, status)
            return
        
        parts = args.split(" ", 1)
        command = parts[0].lower()
        
        if command == "add":
            # Определяем ID пользователя
            user_id = None
            
            if message.is_reply:
                # Используем реплай
                reply = await message.get_reply_message()
                if reply:
                    sender = await reply.get_sender()
                    if sender:
                        user_id = sender.id
            
            if user_id is None and len(parts) > 1:
                # Используем аргумент
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return
            elif user_id is None:
                await utils.answer(message, self.strings['no_reply'])
                return
            
            # Проверка, не в белом списке ли уже
            if self.is_whitelisted(user_id):
                await utils.answer(message, f"<b>Пользователь уже в белом списке!</b>\n\nID: <code>{user_id}</code>")
                return
            
            # Добавление в белый список
            self.add_to_whitelist(user_id, message.sender_id)
            await utils.answer(message, self.strings['whitelist_added'].format(user_id))
            
            # Если у пользователя было сообщение о подписке, удаляем его
            if str(user_id) in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)
                await message.respond(f"<b>Пользователь добавлен в белый список и разблокирован!</b>\n\nID: <code>{user_id}</code>")
        
        elif command == "remove":
            # Определяем ID пользователя
            user_id = None
            
            if message.is_reply:
                # Используем реплай
                reply = await message.get_reply_message()
                if reply:
                    sender = await reply.get_sender()
                    if sender:
                        user_id = sender.id
            
            if user_id is None and len(parts) > 1:
                # Используем аргумент
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return
            elif user_id is None:
                await utils.answer(message, self.strings['no_reply'])
                return
            
            # Удаление из белого списка
            if self.remove_from_whitelist(user_id):
                await utils.answer(message, self.strings['whitelist_removed'].format(user_id))
            else:
                await utils.answer(message, self.strings['whitelist_not_found'])
        
        elif command == "list":
            if not self.whitelist:
                await utils.answer(message, self.strings['whitelist_empty'])
                return
            
            text = f"<b>Белый список пользователей:</b> {len(self.whitelist)}\n\n"
            count = 0
            
            for user_id_str, data in self.whitelist.items():
                try:
                    user_id = int(user_id_str)
                    user_info = f"<b>ID:</b> <code>{user_id}</code>\n"
                    user_info += f"<b>Добавлен:</b> {data.get('added_at', 'Неизвестно')}\n"
                    
                    # Получаем имя пользователя
                    try:
                        user = await self.client.get_entity(user_id)
                        name_parts = []
                        if getattr(user, 'first_name', None):
                            name_parts.append(user.first_name)
                        if getattr(user, 'last_name', None):
                            name_parts.append(user.last_name)
                        
                        name = " ".join(name_parts) if name_parts else "Без имени"
                        
                        if getattr(user, 'username', None):
                            name += f" (@{user.username})"
                        
                        user_info += f"<b>Имя:</b> {name}\n"
                    except:
                        user_info += f"<b>Имя:</b> Неизвестно\n"
                    
                    text += user_info + "─" * 20 + "\n"
                    count += 1
                    
                    # Ограничим вывод чтобы не превысить лимит сообщения
                    if count >= 15:
                        remaining = len(self.whitelist) - count
                        if remaining > 0:
                            text += f"\n<b>И еще {remaining} пользователей...</b>"
                        break
                        
                except Exception as e:
                    continue
            
            await utils.answer(message, text)
        
        elif command == "clear":
            count = len(self.whitelist)
            self.whitelist = {}
            self.db.set("SubChecker", "whitelist", self.whitelist)
            await utils.answer(message, self.strings['whitelist_cleared'].format(count))
        
        elif command == "check":
            # Определяем ID пользователя
            user_id = None
            
            if message.is_reply:
                # Используем реплай
                reply = await message.get_reply_message()
                if reply:
                    sender = await reply.get_sender()
                    if sender:
                        user_id = sender.id
            
            if user_id is None and len(parts) > 1:
                # Используем аргумент
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return
            elif user_id is None:
                await utils.answer(message, self.strings['no_reply'])
                return
            
            # Проверка наличия в белом списке
            if self.is_whitelisted(user_id):
                data = self.whitelist[str(user_id)]
                await utils.answer(message, self.strings['user_in_whitelist'].format(
                    user_id, 
                    data.get('added_at', 'Неизвестно')
                ))
            else:
                await utils.answer(message, self.strings['user_not_in_whitelist'])
        
        else:
            await utils.answer(message, "<b>Неизвестная команда!</b>\n\nИспользуйте .subwl для списка команд")

    @loader.command()
    async def submessage(self, message):
        """Кастомное сообщение, используйте {channel_link} """
        args = utils.get_args_raw(message)
        
        if not args:
            if not self.custom_message:
                await utils.answer(message, self.strings['no_custom_message'])
            else:
                await utils.answer(message, 
                    self.strings['current_custom_message'].format(self.custom_message)
                )
            return
        
        self.custom_message = args
        self.db.set("SubChecker", "custom_message", self.custom_message)
        
        await utils.answer(message, self.strings['custom_message_set'])
    
    @loader.command()
    async def submessageclear(self, message):
        """Сбросить кастомное сообщение"""
        self.custom_message = ""
        self.db.set("SubChecker", "custom_message", self.custom_message)
        
        await utils.answer(message, self.strings['custom_message_cleared'])

    @loader.command()
    async def subchannel(self, message):
        """Настроить канал для проверки подписки [юзернейм или ссылка]"""
        args = utils.get_args_raw(message)
        
        if not args:
            if not self.channel_username:
                await utils.answer(message, self.strings['channel_not_set'])
            else:
                channel_info = f"@{self.channel_username}" if not self.channel_username.startswith('@') else self.channel_username
                if self.channel_link:
                    channel_info = f"<a href='{self.channel_link}'>{channel_info}</a>"
                
                await utils.answer(message, 
                    self.strings['current_channel'].format(
                        channel_info, 
                        self.channel_id if self.channel_id else "Не определен"
                    )
                )
            return
        
        if args.startswith('@'):
            args = args[1:]
        
        if 't.me/' in args:
            if args.startswith('https://'):
                args = args.replace('https://t.me/', '')
            elif args.startswith('t.me/'):
                args = args.replace('t.me/', '')
        
        try:
            channel = await self.client.get_entity(args)
            
            self.channel_username = f"@{channel.username}" if hasattr(channel, 'username') and channel.username else args
            self.channel_id = channel.id
            
            if hasattr(channel, 'username') and channel.username:
                self.channel_link = f"https://t.me/{channel.username}"
            else:
                self.channel_link = f"tg://resolve?domain={args}"
            
            self.db.set("SubChecker", "channel_username", self.channel_username)
            self.db.set("SubChecker", "channel_link", self.channel_link)
            self.db.set("SubChecker", "channel_id", self.channel_id)
            
            channel_display = f"@{channel.username}" if hasattr(channel, 'username') and channel.username else args
            channel_info = f"<a href='{self.channel_link}'>{channel_display}</a>"
            
            await utils.answer(message, 
                self.strings['channel_set'].format(channel_info)
            )
            
            # Перезапускаем фоновую проверку при смене канала
            await self.stop_background_checker()
            
            # Очищаем кэш
            self.subscribers_cache = set()
            self.last_cache_update = None
            
            if self.enabled and self.channel_id:
                await self.start_background_checker()
            
        except Exception as e:
            await utils.answer(message, 
                self.strings['invalid_channel'] + f"\n\n<code>{str(e)}</code>"
            )

    @loader.command()
    async def subtest(self, message):
        """Протестировать доступ к каналу"""
        if not self.channel_id:
            await utils.answer(message, self.strings['channel_not_set'])
            return
        
        try:
            channel = await self.client.get_entity(self.channel_id)
            
            channel_info = []
            if hasattr(channel, 'title'):
                channel_info.append(f"<b>Название:</b> {channel.title}")
            if hasattr(channel, 'username'):
                channel_info.append(f"<b>Юзернейм:</b> @{channel.username}")
            channel_info.append(f"<b>ID:</b> <code>{channel.id}</code>")
            
            # Пробуем получить количество участников
            try:
                count = await self.client.get_participants(self.channel_id, limit=1)
                channel_info.append(f"<b>Доступ к участникам:</b> ✅")
                channel_info.append(f"<b>Примерный размер:</b> {getattr(channel, 'participants_count', 'N/A')}")
            except Exception as e:
                channel_info.append(f"<b>Доступ к участникам:</b> ❌ ({str(e)})")
            
            await utils.answer(message, 
                self.strings['test_success'] + "\n\n" + "\n".join(channel_info)
            )
            
        except Exception as e:
            error_msg = str(e)
            if "CHANNEL_PRIVATE" in error_msg or "аналог is private" in error_msg:
                error_msg = self.strings['no_permission']
            
            await utils.answer(message, 
                self.strings['test_failed'].format(error_msg)
            )

    @loader.command()
    async def subcheck(self, message):
        """Включить/выключить проверку подписки"""
        args = utils.get_args_raw(message)
        
        if args.lower() == "on":
            if not self.channel_id:
                await utils.answer(message, self.strings['channel_not_set'])
                return
                
            self.db.set("SubChecker", "enabled", True)
            self.enabled = True
            
            # Запускаем фоновую проверку
            await self.start_background_checker()
            
        elif args.lower() == "off":
            self.db.set("SubChecker", "enabled", False)
            self.enabled = False
            
            # Останавливаем фоновую проверку
            await self.stop_background_checker()
        
        status_text = "Включена" if self.enabled else "Выключена"
        channel_status = "Настроен" if self.channel_id else "Не настроен"
        whitelist_status = f"{len(self.whitelist)} пользователей"
        blocked_status = f"{len(self.blocked_users)} пользователей"
        
        response = "<b>Статус проверки подписки:</b>\n\n"
        response += f"<b>Проверка:</b> {status_text}\n"
        response += f"<b>Канал:</b> {channel_status}\n"
        response += f"<b>Белый список:</b> {whitelist_status}\n"
        response += f"<b>Заблокировано:</b> {blocked_status}\n"
        response += f"<b>Интервал проверки:</b> {self.check_interval} сек\n"
        
        if self.channel_username:
            response += f"<b>Текущий канал:</b> {self.channel_username}\n"
        
        response += "\n<b>Основные команды:</b>\n"
        response += ".subcheck on/off - вкл/выкл проверку\n"
        response += ".subchannel @юзернейм - установить канал\n"
        response += ".submessage текст - кастомное сообщение\n"
        response += ".subwl - управление белым списком\n"
        response += ".subinterval N - интервал проверки (сек)\n"
        response += ".subblocked - список заблокированных\n"
        response += ".subblockedclear - очистить заблокированных\n"
        response += ".subforcecheck - принудительная проверка\n"
        response += ".subcache - обновить кэш подписчиков\n"
        
        await utils.answer(message, response)

    @loader.command()
    async def subinterval(self, message):
        """Установить интервал проверки подписок (в секундах, минимум 30)"""
        args = utils.get_args_raw(message)
        
        if not args:
            await utils.answer(message, 
                self.strings['current_check_interval'].format(self.check_interval)
            )
            return
        
        try:
            interval = int(args)
            if interval < 30:
                interval = 30
            
            self.check_interval = interval
            self.db.set("SubChecker", "check_interval", interval)
            
            await utils.answer(message, 
                self.strings['check_interval_set'].format(interval)
            )
            
            # Перезапускаем фоновую задачу если она работает
            if self.check_running:
                await self.stop_background_checker()
                await self.start_background_checker()
                
        except ValueError:
            await utils.answer(message, self.strings['invalid_interval'])

    @loader.command()
    async def subblocked(self, message):
        """Показать список заблокированных пользователей"""
        args = utils.get_args_raw(message)
        
        if not self.blocked_users:
            await utils.answer(message, self.strings['no_blocked_users'])
            return
        
        if args:
            # Информация о конкретном пользователе
            try:
                user_id = int(args)
                user_id_str = str(user_id)
                
                if user_id_str not in self.blocked_users:
                    await utils.answer(message, f"<b>Пользователь не найден в списке заблокированных!</b>\n\nID: <code>{user_id}</code>")
                    return
                
                data = self.blocked_users[user_id_str]
                
                # Получаем информацию о пользователе
                try:
                    user = await self.client.get_entity(user_id)
                    name_parts = []
                    if getattr(user, 'first_name', None):
                        name_parts.append(user.first_name)
                    if getattr(user, 'last_name', None):
                        name_parts.append(user.last_name)
                    name = " ".join(name_parts) if name_parts else "Без имени"
                    user_info = f"<b>Имя:</b> {name}\n"
                except:
                    user_info = ""
                
                info = self.strings['blocked_user_info'].format(
                    user_id,
                    data.get('blocked_at', 'Неизвестно'),
                    data.get('check_count', 0),
                    data.get('last_check', 'Никогда')
                )
                
                info = user_info + info
                
                # Проверяем текущий статус подписки
                is_subscribed = await self.check_subscription(user_id)
                sub_status = "✅ Подписан" if is_subscribed else "❌ Не подписан"
                info += f"\n<b>Текущий статус подписки:</b> {sub_status}"
                
                await utils.answer(message, info)
                
            except ValueError:
                await utils.answer(message, self.strings['invalid_user_id'])
            return
        
        # Показываем список всех заблокированных
        text = f"<b>Заблокировано пользователей:</b> {len(self.blocked_users)}\n\n"
        
        count = 0
        for user_id_str, data in self.blocked_users.items():
            try:
                user_id = int(user_id_str)
                try:
                    user = await self.client.get_entity(user_id)
                    name_parts = []
                    if getattr(user, 'first_name', None):
                        name_parts.append(user.first_name)
                    if getattr(user, 'last_name', None):
                        name_parts.append(user.last_name)
                    name = " ".join(name_parts) if name_parts else str(user_id)
                except:
                    name = str(user_id)
                
                blocked_time = data.get('blocked_at', 'Неизвестно')
                check_count = data.get('check_count', 0)
                
                text += f"<b>{name}</b>\nID: <code>{user_id}</code>\nЗаблокирован: {blocked_time}\nПроверок: {check_count}\n"
                text += "─" * 20 + "\n"
                
                count += 1
                if count >= 15:  # Ограничим вывод
                    remaining = len(self.blocked_users) - count
                    if remaining > 0:
                        text += f"\n<b>И еще {remaining} пользователей...</b>"
                    break
                    
            except:
                continue
        
        text += f"\n<b>Интервал проверки:</b> {self.check_interval} секунд"
        text += f"\n<b>Используйте:</b> .subblocked [ID] для подробной информации"
        text += f"\n<b>Очистить список:</b> .subblockedclear"
        
        await utils.answer(message, text)

    @loader.command()
    async def subblockedclear(self, message):
        """Очистить список заблокированных пользователей"""
        if not self.blocked_users:
            await utils.answer(message, self.strings['no_blocked_users'])
            return
        
        # Счетчик для статистики
        count = len(self.blocked_users)
        
        # Получаем список ID пользователей
        user_ids = list(self.blocked_users.keys())
        
        # Разблокируем всех пользователей
        for user_id_str in user_ids:
            try:
                user_id = int(user_id_str)
                await self.unblock_user(user_id, "список заблокированных очищен")
            except:
                pass
        
        # Очищаем список
        self.blocked_users = {}
        self.db.set("SubChecker", "blocked_users", self.blocked_users)
        
        await utils.answer(message, self.strings['blocked_list_cleared'].format(count))

    @loader.command()
    async def subforcecheck(self, message):
        """Принудительная проверка всех заблокированных пользователей"""
        if not self.blocked_users:
            await utils.answer(message, self.strings['no_blocked_users'])
            return
        
        await utils.answer(message, 
            self.strings['force_check_started'].format(len(self.blocked_users))
        )
        
        unblocked_count = 0
        checked_count = 0
        
        # Сначала обновляем кэш
        await self.update_subscribers_cache()
        
        # Проверяем каждого заблокированного пользователя
        for user_id_str in list(self.blocked_users.keys()):
            user_id = int(user_id_str)
            checked_count += 1
            
            # Пропускаем если пользователь в белом списке
            if self.is_whitelisted(user_id):
                await self.unblock_user(user_id, "пользователь в белом списке")
                unblocked_count += 1
                continue
            
            # Проверяем подписку
            is_subscribed = await self.check_subscription(user_id)
            if is_subscribed:
                # Пользователь подписался - разблокируем
                await self.unblock_user(user_id, "подписался на канал")
                unblocked_count += 1
            else:
                # Обновляем счетчик проверок
                self.blocked_users[user_id_str]['check_count'] = self.blocked_users[user_id_str].get('check_count', 0) + 1
                self.blocked_users[user_id_str]['last_check'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db.set("SubChecker", "blocked_users", self.blocked_users)
        
        still_blocked = len(self.blocked_users)
        
        result = self.strings['check_complete'].format(
            checked_count,
            unblocked_count,
            still_blocked
        )
        
        await utils.answer(message, result)

    @loader.command()
    async def sublist(self, message):
        """Показать список пользователей с сообщениями о подписке"""
        if not self.not_subscribed_msgs:
            await utils.answer(message, "Нет пользователей с активными сообщениями о подписке")
            return
        
        text = "<b>Пользователи с сообщениями о подписке:</b>\n\n"
        count = 0
        for user_id_str in self.not_subscribed_msgs:
            user_id = int(user_id_str)
            try:
                user = await self.client.get_entity(user_id)
                name_parts = []
                if getattr(user, 'first_name', None):
                    name_parts.append(user.first_name)
                if getattr(user, 'last_name', None):
                    name_parts.append(user.last_name)
                name = " ".join(name_parts) if name_parts else str(user_id)
                
                is_subscribed = await self.check_subscription(user_id)
                sub_status = "✅ Подписан" if is_subscribed else "❌ Не подписан"
                whitelist_status = "✅ В белом списке" if self.is_whitelisted(user_id) else "❌ Не в белом списке"
                blocked_status = "✅ Заблокирован" if str(user_id) in self.blocked_users else "❌ Не заблокирован"
                
                text += f"{name} (ID: {user_id})\nСтатус: {sub_status}, {whitelist_status}, {blocked_status}\n"
                text += "─" * 20 + "\n"
                count += 1
                
                if count >= 15:
                    remaining = len(self.not_subscribed_msgs) - count
                    if remaining > 0:
                        text += f"\n<b>И еще {remaining} пользователей...</b>"
                    break
            except:
                text += f"ID: {user_id}\n"
                text += "─" * 20 + "\n"
                count += 1
        
        text += f"\n<b>Всего:</b> {count}\n\n"
        text += f"Сообщения автоматически удаляются после подписки на канал"
        
        await utils.answer(message, text)

    @loader.command()
    async def subclean(self, message):
        """Очистить все сообщения о подписке"""
        count = 0
        for user_id_str in list(self.not_subscribed_msgs.keys()):
            user_id = int(user_id_str)
            try:
                await self.client.delete_messages(user_id, self.not_subscribed_msgs[user_id_str])
                count += 1
            except:
                pass
        
        self.not_subscribed_msgs = {}
        self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)
        
        await utils.answer(message, f"<b>Удалено {count} сообщений о подписке</b>")

    @loader.command()
    async def subcache(self, message):
        """Обновить кэш подписчиков"""
        if not self.channel_id:
            await utils.answer(message, self.strings['channel_not_set'])
            return
        
        await utils.answer(message, "<b>Обновление кэша подписчиков...</b>")
        
        if await self.update_subscribers_cache():
            await utils.answer(message, self.strings['subscribers_cache_info'].format(
                len(self.subscribers_cache),
                self.last_cache_update or "Только что"
            ))
        else:
            await utils.answer(message, "<b>Ошибка обновления кэша!</b>")

    @loader.command()
    async def subcacheclear(self, message):
        """Очистить кэш подписчиков"""
        self.subscribers_cache = set()
        self.last_cache_update = None
        self.db.set("SubChecker", "subscribers_cache", {})
        
        await utils.answer(message, self.strings['cache_cleared'])

    async def watcher(self, message):
        """Обработчик входящих сообщений"""
        
        # Проверка включен ли модуль
        if not self.enabled:
            return
        
        # Проверка настроен ли канал
        if not self.channel_id:
            return
            
        # Проверка что сообщение в личке
        if not message.is_private:
            return
        
        # Проверка что сообщение не исходящее
        if message.out:
            return
        
        # Получение информации об отправителе
        try:
            user = await message.get_sender()
        except:
            return
        
        # Проверка что отправитель не бот
        if self.is_bot(user):
            return
        
        user_id = user.id
        
        # Проверка белого списка
        if self.is_whitelisted(user_id):
            # Если пользователь был заблокирован, разблокируем
            if str(user_id) in self.blocked_users:
                await self.unblock_user(user_id, "пользователь в белом списке")
            return
        
        # Проверка подписки через оптимизированный метод
        is_subscribed = await self.check_subscription(user_id)
        
        # Если подписан
        if is_subscribed:
            if str(user_id) in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)
                await message.respond(self.strings['subscribed'])
            
            # Если пользователь был заблокирован, разблокируем
            if str(user_id) in self.blocked_users:
                await self.unblock_user(user_id, "подписался на канал")
            
            return
        
        # Если не подписан
        # Блокируем пользователя
        await self.block_user(user_id)
        
        # Отправляем сообщение о блокировке
        if str(user_id) not in self.not_subscribed_msgs:
            message_text = self.get_not_subscribed_message()
            sent_msg = await message.respond(message_text)
            await self.save_not_subscribed_msg(user_id, sent_msg.id)
        
        await message.delete()

    # При выключении модуля останавливаем фоновую задачу
    async def on_unload(self):
        await self.stop_background_checker
