from telethon import events, Button
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telethon.tl.functions.messages import ReportSpamRequest
from telethon.tl.types import User
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from .. import loader, utils
import json

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
        'bot_detected': "<b>Бот обнаружен!</b>\n\nБоты не проходят проверку подписки.",
        'custom_message_set': "<b>Кастомное сообщение установлено!</b>",
        'custom_message_cleared': "<b>Кастомное сообщение сброшено!</b>",
        'current_custom_message': "<b>Текущее кастомное сообщение:</b>\n\n{}",
        'no_custom_message': "<b>Кастомное сообщение не установлено.</b>\nИспользуется стандартное сообщение.",
        'pinned_enabled': "<b>Закреп сообщений включен!</b>\nСообщения с просьбой подписаться будут закрепляться.",
        'pinned_disabled': "<b>Закреп сообщений отключен!</b>\nСообщения с просьбой подписаться не будут закрепляться.",
        'pinned_status': "<b>Статус закрепа сообщений:</b> {}",
        'whitelist_added': "<b>Пользователь добавлен в белый список!</b>\n\nID: <code>{}</code>\nПричина: {}",
        'whitelist_removed': "<b>Пользователь удален из белого списка!</b>\n\nID: <code>{}</code>",
        'whitelist_not_found': "<b>Пользователь не найден в белом списке!</b>",
        'whitelist_empty': "<b>Белый список пуст!</b>",
        'whitelist_cleared': "<b>Белый список очищен!</b>\n\nУдалено пользователей: {}",
        'whitelist_list': "<b>Белый список пользователей:</b>\n\n{}",
        'whitelist_imported': "<b>Белый список импортирован!</b>\n\nДобавлено пользователей: {}",
        'whitelist_exported': "<b>Белый список экспортирован!</b>\n\nПользователей в файле: {}",
        'whitelist_import_error': "<b>Ошибка импорта белого списка!</b>\n\n{}",
        'user_in_whitelist': "<b>Пользователь в белом списке</b>\n\nID: <code>{}</code>\nПричина: {}\nДобавлен: {}",
        'user_not_in_whitelist': "<b>Пользователь не в белом списке!</b>",
        'invalid_user_id': "<b>Неверный ID пользователя!</b>\nID должен быть числом.",
        'no_reply': "<b>Ответьте на сообщение пользователя или укажите ID!</b>"
    }

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
        
        # Загрузка настройки закрепа
        self.pin_enabled = self.db.get("SubChecker", "pin_enabled", True)
        
        # Загрузка белого списка
        self.whitelist = self.db.get("SubChecker", "whitelist", {})
        
        # Включение/выключение модуля
        self.enabled = self.db.get("SubChecker", "enabled", True)

    async def check_subscription(self, user_id):
        """Проверка подписки пользователя на канал"""
        if not self.channel_id:
            return False
        
        try:
            participants = await self.client.get_participants(self.channel_id, limit=10000)
            return any(participant.id == user_id for participant in participants)
        except Exception as e:
            print(f"Ошибка проверки подписки: {e}")
            return False

    def is_bot(self, user):
        """Проверка, является ли пользователь ботом"""
        if isinstance(user, User):
            return user.bot
        return False

    def is_whitelisted(self, user_id):
        """Проверка, находится ли пользователь в белом списке"""
        return str(user_id) in self.whitelist

    def add_to_whitelist(self, user_id, reason="Не указана", added_by=None):
        """Добавление пользователя в белый список"""
        from datetime import datetime
        self.whitelist[str(user_id)] = {
            'reason': reason,
            'added_by': added_by,
            'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_id': user_id
        }
        self.db.set("SubChecker", "whitelist", self.whitelist)

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

    async def pin_message(self, user_id, message_id):
        """Закрепление сообщения"""
        if self.pin_enabled:
            try:
                await self.client(UpdatePinnedMessageRequest(
                    peer=user_id,
                    id=message_id,
                    silent=True,
                    unpin=False
                ))
                print(f"Сообщение {message_id} закреплено для пользователя {user_id}")
            except Exception as e:
                print(f"Ошибка при закреплении сообщения: {e}")

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
            status += ".subwl add [ID] [причина] - добавить пользователя\n"
            status += ".subwl remove [ID] - удалить пользователя\n"
            status += ".subwl list - показать список\n"
            status += ".subwl clear - очистить список\n"
            status += ".subwl check [ID] - проверить пользователя\n"
            status += ".subwl import - импорт из JSON\n"
            status += ".subwl export - экспорт в JSON\n"
            await utils.answer(message, status)
            return
        
        parts = args.split(" ", 1)
        command = parts[0].lower()
        
        if command == "add":
            if len(parts) < 2:
                await utils.answer(message, "<b>Используйте:</b> .subwl add [ID] [причина]\n<b>Или ответьте на сообщение пользователя:</b> .subwl add [причина]")
                return
            
            # Проверка, есть ли reply
            if message.is_reply:
                reply = await message.get_reply_message()
                user = await reply.get_sender()
                user_id = user.id
                reason = parts[1] if len(parts) > 1 else "Не указана"
            else:
                try:
                    user_id = int(parts[1].split()[0])
                    reason = parts[1].split(" ", 1)[1] if len(parts[1].split()) > 1 else "Не указана"
                except (ValueError, IndexError):
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return
            
            # Проверка, не в белом списке ли уже
            if self.is_whitelisted(user_id):
                await utils.answer(message, f"<b>Пользователь уже в белом списке!</b>\n\nID: <code>{user_id}</code>")
                return
            
            # Добавление в белый список
            self.add_to_whitelist(user_id, reason, message.sender_id)
            await utils.answer(message, self.strings['whitelist_added'].format(user_id, reason))
            
            # Если у пользователя было сообщение о подписке, удаляем его
            if str(user_id) in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)
                await message.respond(f"<b>Пользователь добавлен в белый список и разблокирован!</b>\n\nID: <code>{user_id}</code>")
        
        elif command == "remove":
            if len(parts) < 2:
                await utils.answer(message, "<b>Используйте:</b> .subwl remove [ID]\n<b>Или ответьте на сообщение пользователя:</b> .subwl remove")
                return
            
            # Проверка, есть ли reply
            if message.is_reply:
                reply = await message.get_reply_message()
                user = await reply.get_sender()
                user_id = user.id
            else:
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
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
            
            text = self.strings['whitelist_list'].format("")
            count = 0
            
            for user_id_str, data in self.whitelist.items():
                try:
                    user_id = int(user_id_str)
                    user_info = f"<b>ID:</b> <code>{user_id}</code>\n"
                    user_info += f"<b>Причина:</b> {data.get('reason', 'Не указана')}\n"
                    user_info += f"<b>Добавлен:</b> {data.get('added_at', 'Неизвестно')}\n"
                    
                    # Попробуем получить имя пользователя
                    try:
                        user = await self.client.get_entity(user_id)
                        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or "Неизвестно"
                        user_info += f"<b>Имя:</b> {name}\n"
                    except:
                        user_info += f"<b>Имя:</b> Не удалось получить\n"
                    
                    text += user_info + "─" * 20 + "\n"
                    count += 1
                    
                    # Ограничим вывод чтобы не превысить лимит сообщения
                    if count >= 20:
                        text += f"\n<b>И еще:</b> {len(self.whitelist) - count} пользователей..."
                        break
                        
                except Exception as e:
                    continue
            
            text = self.strings['whitelist_list'].format(f"Всего: {len(self.whitelist)}\n\n") + text
            await utils.answer(message, text)
        
        elif command == "clear":
            count = len(self.whitelist)
            self.whitelist = {}
            self.db.set("SubChecker", "whitelist", self.whitelist)
            await utils.answer(message, self.strings['whitelist_cleared'].format(count))
        
        elif command == "check":
            if len(parts) < 2:
                await utils.answer(message, "<b>Используйте:</b> .subwl check [ID]\n<b>Или ответьте на сообщение пользователя:</b> .subwl check")
                return
            
            # Проверка, есть ли reply
            if message.is_reply:
                reply = await message.get_reply_message()
                user = await reply.get_sender()
                user_id = user.id
            else:
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return
            
            # Проверка наличия в белом списке
            if self.is_whitelisted(user_id):
                data = self.whitelist[str(user_id)]
                await utils.answer(message, self.strings['user_in_whitelist'].format(
                    user_id, 
                    data.get('reason', 'Не указана'),
                    data.get('added_at', 'Неизвестно')
                ))
            else:
                await utils.answer(message, self.strings['user_not_in_whitelist'])
        
        elif command == "import":
            if not message.file:
                await utils.answer(message, "<b>Прикрепите JSON файл с белым списком!</b>\n\nФормат: [{'user_id': 123456, 'reason': 'причина'}, ...]")
                return
            
            try:
                file = await message.download_media(bytes)
                data = json.loads(file.decode('utf-8'))
                
                imported = 0
                for item in data:
                    if 'user_id' in item:
                        user_id = item['user_id']
                        reason = item.get('reason', 'Импортировано')
                        if not self.is_whitelisted(user_id):
                            self.add_to_whitelist(user_id, reason, message.sender_id)
                            imported += 1
                
                await utils.answer(message, self.strings['whitelist_imported'].format(imported))
                
            except Exception as e:
                await utils.answer(message, self.strings['whitelist_import_error'].format(str(e)))
        
        elif command == "export":
            if not self.whitelist:
                await utils.answer(message, self.strings['whitelist_empty'])
                return
            
            # Создаем список для экспорта
            export_list = []
            for user_id_str, data in self.whitelist.items():
                export_list.append({
                    'user_id': int(user_id_str),
                    'reason': data.get('reason', 'Не указана'),
                    'added_by': data.get('added_by'),
                    'added_at': data.get('added_at'),
                    'exported_at': utils.get_datetime_now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # Сохраняем в JSON
            json_data = json.dumps(export_list, indent=2, ensure_ascii=False)
            filename = f"whitelist_{utils.get_datetime_now().strftime('%Y%m%d_%H%M%S')}.json"
            
            await message.respond(
                file=json_data.encode('utf-8'),
                attributes=[types.DocumentAttributeFilename(filename)]
            )
            
            await utils.answer(message, self.strings['whitelist_exported'].format(len(export_list)))
        
        else:
            await utils.answer(message, "<b>Неизвестная команда!</b>\n\nИспользуйте .subwl для списка команд")

    @loader.command()
    async def subpin(self, message):
        """Включить/выключить закреп сообщений"""
        args = utils.get_args_raw(message)
        
        if args.lower() == "on":
            self.pin_enabled = True
            self.db.set("SubChecker", "pin_enabled", True)
            status_text = "Включен"
            await utils.answer(message, self.strings['pinned_enabled'])
        elif args.lower() == "off":
            self.pin_enabled = False
            self.db.set("SubChecker", "pin_enabled", False)
            status_text = "Выключен"
            await utils.answer(message, self.strings['pinned_disabled'])
        else:
            status_text = "Включен" if self.pin_enabled else "Выключен"
            await utils.answer(message, self.strings['pinned_status'].format(status_text))

    @loader.command()
    async def submessage(self, message):
        """Установить кастомное сообщение для проверки подписки"""
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
            participants = await self.client.get_participants(self.channel_id, limit=1)
            
            channel_info = []
            if hasattr(channel, 'title'):
                channel_info.append(f"<b>Название:</b> {channel.title}")
            if hasattr(channel, 'username'):
                channel_info.append(f"<b>Юзернейм:</b> @{channel.username}")
            channel_info.append(f"<b>ID:</b> <code>{channel.id}</code>")
            channel_info.append(f"<b>Участников:</b> {channel.participants_count if hasattr(channel, 'participants_count') else 'N/A'}")
            
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
        
        enabled = self.db.get("SubChecker", "enabled", True)
        
        if args.lower() == "on":
            if not self.channel_id:
                await utils.answer(message, self.strings['channel_not_set'])
                return
                
            self.db.set("SubChecker", "enabled", True)
            self.enabled = True
        elif args.lower() == "off":
            self.db.set("SubChecker", "enabled", False)
            self.enabled = False
        
        status_text = "Включена" if self.enabled else "Выключена"
        channel_status = "Настроен" if self.channel_id else "Не настроен"
        pin_status = "Включен" if self.pin_enabled else "Выключен"
        whitelist_status = f"{len(self.whitelist)} пользователей"
        
        response = "<b>Статус проверки подписки:</b>\n\n"
        response += f"<b>Проверка:</b> {status_text}\n"
        response += f"<b>Канал:</b> {channel_status}\n"
        response += f"<b>Закреп сообщений:</b> {pin_status}\n"
        response += f"<b>Белый список:</b> {whitelist_status}\n"
        
        if self.channel_username:
            response += f"<b>Текущий канал:</b> {self.channel_username}\n"
        
        response += "\n<b>Основные команды:</b>\n"
        response += ".subcheck on/off - вкл/выкл проверку\n"
        response += ".subchannel @юзернейм - установить канал\n"
        response += ".submessage текст - кастомное сообщение\n"
        response += ".subpin on/off - закреп сообщений\n"
        response += ".subwl - управление белым списком\n"
        
        await utils.answer(message, response)

    async def watcher(self, message):
        """Обработчик входящих сообщений"""
        
        # Проверка включен ли модуль
        if not self.enabled:
            return
        
        # Проверка настроен ли канал
        if not self.channel_id:
            print("Канал не настроен")
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
            print("Не удалось получить информацию об отправителе")
            return
        
        # Проверка что отправитель не бот
        if self.is_bot(user):
            print(f"Сообщение от бота {user.id}, игнорируем")
            return
        
        user_id = user.id
        
        # Проверка белого списка
        if self.is_whitelisted(user_id):
            print(f"Пользователь {user_id} в белом списке, проверка подписки пропускается")
            return
        
        # Проверка подписки
        is_subscribed = await self.check_subscription(user_id)
        
        # Если подписан
        if is_subscribed:
            if str(user_id) in self.not_subscribed_msgs:
                print(f"Пользователь {user_id} подписался, удаляем сообщение с просьбой подписаться")
                await self.delete_not_subscribed_msg(user_id)
                await message.respond(self.strings['subscribed'])
            return
        
        # Если не подписан
        print(f"Пользователь {user_id} не подписан, удаляем сообщение")
        
        if str(user_id) not in self.not_subscribed_msgs:
            message_text = self.get_not_subscribed_message()
            sent_msg = await message.respond(message_text)
            await self.pin_message(user_id, sent_msg.id)
            await self.save_not_subscribed_msg(user_id, sent_msg.id)
        
        await message.delete()

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
                name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or str(user_id)
                
                is_subscribed = await self.check_subscription(user_id)
                sub_status = "Подписан" if is_subscribed else "Не подписан"
                whitelist_status = "В белом списке" if self.is_whitelisted(user_id) else "Не в белом списке"
                
                text += f"{name} (ID: {user_id})\nСтатус: {sub_status}, {whitelist_status}\n"
                count += 1
            except:
                text += f"ID: {user_id}\n"
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
