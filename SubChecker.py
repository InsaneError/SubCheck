from telethon import events, Button
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.types import InputPeerChannel
from telethon.errors import ChatAdminRequiredError
from .. import loader, utils
import asyncio

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

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "channel_username",
                "",
                "Юзернейм канала для проверки подписки",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "channel_link",
                "",
                "Ссылка на канал",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "channel_id",
                None,
                "ID канала",
                validator=loader.validators.Union(
                    loader.validators.NoneType(),
                    loader.validators.Integer()
                )
            ),
            loader.ConfigValue(
                "custom_message",
                "",
                "Кастомное сообщение (используйте {channel_link})",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "pin_enabled",
                True,
                "Включить закреп сообщений",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "enabled",
                True,
                "Включить проверку подписки",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "not_subscribed_msgs",
                {},
                "ID сообщений о неподписке",
                validator=loader.validators.Dict()
            ),
            loader.ConfigValue(
                "whitelist",
                {},
                "Белый список пользователей",
                validator=loader.validators.Dict()
            )
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        
        # Загрузка настроек из конфига
        self.channel_username = self.config["channel_username"]
        self.channel_link = self.config["channel_link"]
        self.channel_id = self.config["channel_id"]
        
        # Загрузка сообщений о неподписке
        self.not_subscribed_msgs = self.config["not_subscribed_msgs"]
        
        # Загрузка кастомного сообщения
        self.custom_message = self.config["custom_message"]
        
        # Загрузка настройки закрепа
        self.pin_enabled = self.config["pin_enabled"]
        
        # Загрузка белого списка
        self.whitelist = self.config["whitelist"]
        
        # Включение/выключение модуля
        self.enabled = self.config["enabled"]

    async def check_subscription(self, user_id):
        """Проверка подписки пользователя на канал"""
        if not self.channel_id:
            return False
        
        try:
            # Получаем сущность канала
            channel = await self.client.get_entity(self.channel_id)
            
            # Проверяем, является ли канал супергруппой или каналом
            if hasattr(channel, 'migrated_to') and channel.migrated_to:
                # Канал был преобразован в супергруппу
                channel_id = channel.migrated_to.channel_id
                access_hash = channel.migrated_to.access_hash
                channel_entity = InputPeerChannel(channel_id, access_hash)
            else:
                channel_entity = channel
            
            # Получаем участников канала
            participants = await self.client.get_participants(channel_entity, limit=1000)
            
            # Проверяем наличие пользователя среди участников
            for participant in participants:
                if participant.id == user_id:
                    return True
            
            # Если не нашли в первых 1000 участниках, проверяем конкретно этого пользователя
            try:
                participant = await self.client.get_permissions(channel_entity, user_id)
                return participant.is_user
            except:
                return False
                
        except Exception as e:
            print(f"Ошибка проверки подписки: {e}")
            return False

    def is_bot(self, user):
        """Проверка, является ли пользователь ботом"""
        if hasattr(user, 'bot'):
            return user.bot
        return False

    def is_whitelisted(self, user_id):
        """Проверка, находится ли пользователь в белом списке"""
        return str(user_id) in self.whitelist

    def add_to_whitelist(self, user_id, added_by=None):
        """Добавление пользователя в белый список"""
        from datetime import datetime
        self.whitelist[str(user_id)] = {
            'added_by': added_by,
            'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_id': user_id
        }
        self.config["whitelist"] = self.whitelist

    def remove_from_whitelist(self, user_id):
        """Удаление пользователя из белого списка"""
        if str(user_id) in self.whitelist:
            del self.whitelist[str(user_id)]
            self.config["whitelist"] = self.whitelist
            return True
        return False

    async def save_not_subscribed_msg(self, user_id, message_id):
        """Сохранение ID сообщения о неподписке"""
        self.not_subscribed_msgs[str(user_id)] = message_id
        self.config["not_subscribed_msgs"] = self.not_subscribed_msgs

    async def delete_not_subscribed_msg(self, user_id):
        """Удаление сообщения о неподписке"""
        if str(user_id) in self.not_subscribed_msgs:
            try:
                await self.client.delete_messages(user_id, self.not_subscribed_msgs[str(user_id)])
            except:
                pass
            del self.not_subscribed_msgs[str(user_id)]
            self.config["not_subscribed_msgs"] = self.not_subscribed_msgs

    async def pin_message(self, user_id, message_id):
        """Закрепление сообщения с удалением системного уведомления"""
        if self.pin_enabled:
            try:
                # Задержка перед закреплением
                await asyncio.sleep(0.5)
                
                # Закрепляем сообщение без уведомления
                await self.client(UpdatePinnedMessageRequest(
                    peer=user_id,
                    id=message_id,
                    silent=True,
                    unpin=False
                ))
                
                # Удаляем системное уведомление о закреплении
                await asyncio.sleep(1)  # Даем время для создания уведомления
                try:
                    # Получаем последние сообщения
                    messages = await self.client.get_messages(user_id, limit=5)
                    
                    for msg in messages:
                        # Проверяем, является ли сообщение системным уведомлением о закреплении
                        if (msg.action is not None and 
                            hasattr(msg.action, '_') and 
                            msg.action._ == 'MessageActionPinMessage'):
                            await msg.delete()
                            print(f"Удалено системное уведомление о закреплении для пользователя {user_id}")
                            break
                except Exception as e:
                    print(f"Не удалось удалить системное уведомление: {e}")
                
                print(f"Сообщение {message_id} закреплено для пользователя {user_id}")
                
            except ChatAdminRequiredError:
                print(f"Нет прав для закрепления сообщений у пользователя {user_id}")
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
            if len(parts) < 2:
                await utils.answer(message, "<b>Используйте:</b> .subwl add [ID]\n<b>Или ответьте на сообщение пользователя:</b> .subwl add")
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
            
            text = "<b>Белый список пользователей:</b>\n\n"
            count = 0
            
            for user_id_str, data in self.whitelist.items():
                try:
                    user_id = int(user_id_str)
                    user_info = f"<b>ID:</b> <code>{user_id}</code>\n"
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
            self.config["whitelist"] = self.whitelist
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
                    data.get('added_at', 'Неизвестно')
                ))
            else:
                await utils.answer(message, self.strings['user_not_in_whitelist'])
        
        else:
            await utils.answer(message, "<b>Неизвестная команда!</b>\n\nИспользуйте .subwl для списка команд")

    @loader.command()
    async def subpin(self, message):
        """Включить/выключить закреп сообщений"""
        args = utils.get_args_raw(message)
        
        if args.lower() == "on":
            self.pin_enabled = True
            self.config["pin_enabled"] = True
            status_text = "Включен"
            await utils.answer(message, self.strings['pinned_enabled'])
        elif args.lower() == "off":
            self.pin_enabled = False
            self.config["pin_enabled"] = False
            status_text = "Выключен"
            await utils.answer(message, self.strings['pinned_disabled'])
        else:
            status_text = "Включен" if self.pin_enabled else "Выключен"
            await utils.answer(message, self.strings['pinned_status'].format(status_text))

    @loader.command()
    async def submessage(self, message):
        """Кастомное сообщение, используйте {channel_link}"""
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
        self.config["custom_message"] = self.custom_message
        
        await utils.answer(message, self.strings['custom_message_set'])
    
    @loader.command()
    async def submessageclear(self, message):
        """Сбросить кастомное сообщение"""
        self.custom_message = ""
        self.config["custom_message"] = self.custom_message
        
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
            
            self.config["channel_username"] = self.channel_username
            self.config["channel_link"] = self.channel_link
            self.config["channel_id"] = self.channel_id
            
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
        
        if args.lower() == "on":
            if not self.channel_id:
                await utils.answer(message, self.strings['channel_not_set'])
                return
                
            self.config["enabled"] = True
            self.enabled = True
        elif args.lower() == "off":
            self.config["enabled"] = False
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
            return
        
        # Проверка подписки
        is_subscribed = await self.check_subscription(user_id)
        
        # Если подписан
        if is_subscribed:
            if str(user_id) in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)
                await message.respond(self.strings['subscribed'])
            return
        
        # Если не подписан
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
        self.config["not_subscribed_msgs"] = self.not_subscribed_msgs
        
        await utils.answer(message, f"<b>Удалено {count} сообщений о подписке</b>")
