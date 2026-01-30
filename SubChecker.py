from telethon import events
from collections import defaultdict
import time
from .. import loader, utils

@loader.tds
class SubCheckBot(loader.Module):
    """Буст канала от @InsModule"""
    
    strings = {
        'name': 'SubChecker',
        'not_subscribed': "<b>Вы не подписаны на наш канал!</b>\nПожалуйста, подпишитесь на канал {channel_link}, чтобы продолжить общение.",
        'subscribed': "<b>Спасибо за подписку! Теперь вы можете свободно писать в лс.</b>",
        'channel_not_set': "<b>Канал для проверки подписки не настроен!</b>\n\nИспользуйте команду .subchannel [юзернейм или ссылка] для настройки канала.\nПример: .subchannel @my_channel",
        'channel_set': "<b>Канал для проверки подписки установлен:</b> {}",
        'current_channel': "<b>Текущий канал для проверки:</b> {}\n\n<b>ID канала:</b> <code>{}</code>",
        'invalid_channel': "<b>Не удалось найти канал!</b>\n\nПроверьте правильность юзернейма или ссылки и убедитесь, что бот имеет доступ к каналу.",
        'test_success': "<b>Тест пройден успешно!</b>\n\nБот может получить информацию о канале и его участниках.",
        'test_failed': "<b>Тест не пройден!</b>\n\nОшибка: {}",
        'no_permission': "<b>Нет прав доступа!</b>\n\nУбедитесь, что бот является администратором канала или имеет права на просмотр участников.",
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
        'no_reply': "<b>Ответьте на сообщение пользователя или укажите ID!</b>"
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        
        # Кэш для быстрого доступа
        self._cache = {
            'channel_id': None,
            'whitelist': set(),
            'pending_users': set(),  # Пользователи, которым уже отправлено сообщение
            'last_check': {}  # Время последней проверки для каждого пользователя
        }
        
        # Загрузка настроек
        self.channel_username = self.db.get("SubChecker", "channel_username", "")
        self.channel_link = self.db.get("SubChecker", "channel_link", "")
        self.channel_id = self.db.get("SubChecker", "channel_id")
        
        # Кэшируем ID канала
        if self.channel_id:
            self._cache['channel_id'] = self.channel_id
        
        # Загрузка кастомного сообщения
        self.custom_message = self.db.get("SubChecker", "custom_message", "")
        
        # Загрузка белого списка
        whitelist_data = self.db.get("SubChecker", "whitelist", {})
        self._cache['whitelist'] = set(str(uid) for uid in whitelist_data.keys())
        
        # Включение/выключение модуля
        self.enabled = self.db.get("SubChecker", "enabled", True)
        
        # Флаг для предотвращения дублирования
        self._processing = defaultdict(bool)

    async def check_subscription(self, user_id):
        """Проверка подписки пользователя на канал с кэшированием"""
        if not self._cache['channel_id']:
            return False
        
        # Проверяем кэш (5 минут)
        cache_key = f"sub_{user_id}"
        if cache_key in self._cache['last_check']:
            if time.time() - self._cache['last_check'][cache_key] < 300:  # 5 минут
                return True
        
        try:
            # Используем более быстрый метод проверки
            async for participant in self.client.iter_participants(
                self._cache['channel_id'], 
                limit=1, 
                filter=User(id=user_id)
            ):
                self._cache['last_check'][cache_key] = time.time()
                return True
            return False
        except Exception:
            return False

    def is_whitelisted(self, user_id):
        """Быстрая проверка белого списка через set"""
        return str(user_id) in self._cache['whitelist']

    def add_to_whitelist(self, user_id):
        """Добавление пользователя в белый список"""
        user_str = str(user_id)
        if user_str not in self._cache['whitelist']:
            self._cache['whitelist'].add(user_str)
            # Сохраняем в базу
            whitelist_data = self.db.get("SubChecker", "whitelist", {})
            whitelist_data[user_str] = {
                'added_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                'user_id': user_id
            }
            self.db.set("SubChecker", "whitelist", whitelist_data)

    def remove_from_whitelist(self, user_id):
        """Удаление пользователя из белого списка"""
        user_str = str(user_id)
        if user_str in self._cache['whitelist']:
            self._cache['whitelist'].remove(user_str)
            # Удаляем из базы
            whitelist_data = self.db.get("SubChecker", "whitelist", {})
            whitelist_data.pop(user_str, None)
            self.db.set("SubChecker", "whitelist", whitelist_data)
            return True
        return False

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
            total_users = len(self._cache['whitelist'])
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
            user_id = None
            
            if message.is_reply:
                reply = await message.get_reply_message()
                user = await reply.get_sender()
                user_id = user.id
            elif len(parts) > 1:
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return
            else:
                await utils.answer(message, "<b>Используйте:</b> .subwl add [ID]\n<b>Или ответьте на сообщение</b>")
                return
            
            if self.is_whitelisted(user_id):
                await utils.answer(message, f"<b>Уже в белом списке!</b>\n\nID: <code>{user_id}</code>")
                return
            
            self.add_to_whitelist(user_id)
            await utils.answer(message, self.strings['whitelist_added'].format(user_id))
            
            # Удаляем из pending, если был там
            self._cache['pending_users'].discard(str(user_id))
        
        elif command == "remove":
            user_id = None
            
            if message.is_reply:
                reply = await message.get_reply_message()
                user = await reply.get_sender()
                user_id = user.id
            elif len(parts) > 1:
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return
            else:
                await utils.answer(message, "<b>Используйте:</b> .subwl remove [ID]\n<b>Или ответьте на сообщение</b>")
                return
            
            if self.remove_from_whitelist(user_id):
                await utils.answer(message, self.strings['whitelist_removed'].format(user_id))
            else:
                await utils.answer(message, self.strings['whitelist_not_found'])
        
        elif command == "list":
            if not self._cache['whitelist']:
                await utils.answer(message, self.strings['whitelist_empty'])
                return
            
            whitelist_data = self.db.get("SubChecker", "whitelist", {})
            text = f"<b>Белый список:</b> {len(self._cache['whitelist'])} пользователей\n\n"
            
            for i, user_str in enumerate(list(self._cache['whitelist'])[:20], 1):
                data = whitelist_data.get(user_str, {})
                text += f"{i}. ID: <code>{user_str}</code>\n"
                text += f"   Добавлен: {data.get('added_at', 'Неизвестно')}\n"
                
                if i < min(20, len(self._cache['whitelist'])):
                    text += "   \n"
            
            if len(self._cache['whitelist']) > 20:
                text += f"\n<b>И еще:</b> {len(self._cache['whitelist']) - 20} пользователей..."
            
            await utils.answer(message, text)
        
        elif command == "clear":
            count = len(self._cache['whitelist'])
            self._cache['whitelist'].clear()
            self.db.set("SubChecker", "whitelist", {})
            await utils.answer(message, self.strings['whitelist_cleared'].format(count))
        
        elif command == "check":
            user_id = None
            
            if message.is_reply:
                reply = await message.get_reply_message()
                user = await reply.get_sender()
                user_id = user.id
            elif len(parts) > 1:
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return
            else:
                await utils.answer(message, "<b>Используйте:</b> .subwl check [ID]\n<b>Или ответьте на сообщение</b>")
                return
            
            if self.is_whitelisted(user_id):
                whitelist_data = self.db.get("SubChecker", "whitelist", {})
                data = whitelist_data.get(str(user_id), {})
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
                await utils.answer(message, self.strings['current_custom_message'].format(self.custom_message))
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
                
                await utils.answer(message, self.strings['current_channel'].format(
                    channel_info, 
                    self.channel_id if self.channel_id else "Не определен"
                ))
            return
        
        # Очистка аргументов
        if args.startswith('@'):
            args = args[1:]
        
        if 't.me/' in args:
            args = args.split('/')[-1]
        
        try:
            entity = await self.client.get_entity(args)
            
            if not hasattr(entity, 'broadcast') or not entity.broadcast:
                await utils.answer(message, "<b>Это не канал!</b>\nУкажите канал для проверки подписки.")
                return
            
            self.channel_username = f"@{entity.username}" if entity.username else args
            self.channel_id = entity.id
            self._cache['channel_id'] = entity.id
            
            if entity.username:
                self.channel_link = f"https://t.me/{entity.username}"
            else:
                self.channel_link = f"tg://resolve?domain={entity.id}"
            
            self.db.set("SubChecker", "channel_username", self.channel_username)
            self.db.set("SubChecker", "channel_link", self.channel_link)
            self.db.set("SubChecker", "channel_id", self.channel_id)
            
            channel_display = f"@{entity.username}" if entity.username else args
            channel_info = f"<a href='{self.channel_link}'>{channel_display}</a>"
            
            await utils.answer(message, self.strings['channel_set'].format(channel_info))
            
        except Exception as e:
            await utils.answer(message, self.strings['invalid_channel'] + f"\n\n<code>{str(e)}</code>")

    @loader.command()
    async def subtest(self, message):
        """Протестировать доступ к каналу"""
        if not self._cache['channel_id']:
            await utils.answer(message, self.strings['channel_not_set'])
            return
        
        try:
            channel = await self.client.get_entity(self._cache['channel_id'])
            participants_count = channel.participants_count if hasattr(channel, 'participants_count') else 'N/A'
            
            channel_info = []
            if hasattr(channel, 'title'):
                channel_info.append(f"<b>Название:</b> {channel.title}")
            if hasattr(channel, 'username'):
                channel_info.append(f"<b>Юзернейм:</b> @{channel.username}")
            channel_info.append(f"<b>ID:</b> <code>{channel.id}</code>")
            channel_info.append(f"<b>Участников:</b> {participants_count}")
            
            await utils.answer(message, self.strings['test_success'] + "\n\n" + "\n".join(channel_info))
            
        except Exception as e:
            error_msg = str(e)
            if any(x in error_msg.lower() for x in ['private', 'rights', 'access']):
                error_msg = self.strings['no_permission']
            
            await utils.answer(message, self.strings['test_failed'].format(error_msg))

    @loader.command()
    async def subcheck(self, message):
        """Включить/выключить проверку подписки"""
        args = utils.get_args_raw(message)
        
        if args.lower() == "on":
            if not self._cache['channel_id']:
                await utils.answer(message, self.strings['channel_not_set'])
                return
                
            self.db.set("SubChecker", "enabled", True)
            self.enabled = True
            status = "✅ Включена"
        elif args.lower() == "off":
            self.db.set("SubChecker", "enabled", False)
            self.enabled = False
            status = "❌ Выключена"
        else:
            status = "✅ Включена" if self.enabled else "❌ Выключена"
        
        response = f"<b>Статус проверки подписки:</b> {status}\n\n"
        
        if self.channel_username:
            response += f"<b>Канал:</b> {self.channel_username}\n"
        else:
            response += "<b>Канал:</b> ❌ Не настроен\n"
        
        response += f"<b>Белый список:</b> {len(self._cache['whitelist'])} пользователей\n"
        
        response += "\n<b>Основные команды:</b>\n"
        response += ".subcheck on/off - вкл/выкл проверку\n"
        response += ".subchannel @юзернейм - установить канал\n"
        response += ".submessage текст - кастомное сообщение\n"
        response += ".subwl - управление белым списком\n"
        
        await utils.answer(message, response)

    async def watcher(self, message):
        """Оптимизированный обработчик входящих сообщений"""
        
        # Быстрые проверки
        if not self.enabled or not self._cache['channel_id'] or not message.is_private or message.out:
            return
        
        try:
            user = await message.get_sender()
            user_id = user.id
            user_str = str(user_id)
            
            # Проверка на бота
            if hasattr(user, 'bot') and user.bot:
                return
            
            # Проверка флага обработки (предотвращение дублирования)
            if self._processing[user_str]:
                return
            self._processing[user_str] = True
            
            # Проверка белого списка
            if self.is_whitelisted(user_id):
                self._processing[user_str] = False
                return
            
            # Проверяем, не отправляли ли уже сообщение
            if user_str in self._cache['pending_users']:
                # Проверяем подписку
                if await self.check_subscription(user_id):
                    # Пользователь подписался
                    self._cache['pending_users'].discard(user_str)
                    await message.respond(self.strings['subscribed'])
                    await message.delete()
                self._processing[user_str] = False
                return
            
            # Первое сообщение - проверяем подписку
            if await self.check_subscription(user_id):
                self._processing[user_str] = False
                return
            
            # Пользователь не подписан
            self._cache['pending_users'].add(user_str)
            message_text = self.get_not_subscribed_message()
            await message.respond(message_text)
            await message.delete()
            
        except Exception as e:
            print(f"Ошибка в watcher: {e}")
        finally:
            if 'user_str' in locals():
                self._processing[user_str] = False

    @loader.command()
    async def sublist(self, message):
        """Показать список пользователей ожидающих подписки"""
        if not self._cache['pending_users']:
            await utils.answer(message, "Нет пользователей ожидающих подписки")
            return
        
        text = f"<b>Пользователи ожидающие подписку:</b> {len(self._cache['pending_users'])}\n\n"
        
        for i, user_str in enumerate(list(self._cache['pending_users'])[:15], 1):
            try:
                user_id = int(user_str)
                user = await self.client.get_entity(user_id)
                name = user.first_name or user.username or user_str
                text += f"{i}. {name} (ID: {user_id})\n"
            except:
                text += f"{i}. ID: {user_str}\n"
        
        if len(self._cache['pending_users']) > 15:
            text += f"\n<b>И еще:</b> {len(self._cache['pending_users']) - 15} пользователей..."
        
        text += "\n\nСообщения автоматически удаляются после подписки"
        
        await utils.answer(message, text)

    @loader.command()
    async def subclean(self, message):
        """Очистить список ожидающих"""
        count = len(self._cache['pending_users'])
        self._cache['pending_users'].clear()
        await utils.answer(message, f"<b>Очищено {count} пользователей из списка ожидания</b>")
