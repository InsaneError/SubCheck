from telethon import events, Button
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
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

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._me = await client.get_me()
        
        # Загрузка настроек из конфига
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "channel_username",
                "",
                "Юзернейм канала (без @)",
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
                    loader.validators.Integer(),
                    loader.validators.NoneType()
                )
            ),
            loader.ConfigValue(
                "custom_message",
                "",
                "Кастомное сообщение",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "pin_enabled",
                True,
                "Закреп сообщений",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "enabled",
                True,
                "Включить проверку подписки",
                validator=loader.validators.Boolean()
            )
        )
        
        # Загрузка данных из базы
        self.not_subscribed_msgs = self.db.get("SubChecker", "not_subscribed_msgs", {})
        self.whitelist = self.db.get("SubChecker", "whitelist", {})

    async def check_subscription(self, user_id):
        """Проверка подписки пользователя на канал"""
        if not self.config["channel_id"]:
            return False
        
        try:
            # Оптимизированная проверка подписки
            async for participant in self.client.iter_participants(
                self.config["channel_id"], 
                limit=100
            ):
                if participant.id == user_id:
                    return True
        except Exception as e:
            print(f"Ошибка проверки подписки: {e}")
        return False

    def is_bot(self, user):
        """Проверка, является ли пользователь ботом"""
        return getattr(user, 'bot', False)

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
        self.db.set("SubChecker", "whitelist", self.whitelist)

    def remove_from_whitelist(self, user_id):
        """Удаление пользователя из белого списка"""
        user_id_str = str(user_id)
        if user_id_str in self.whitelist:
            del self.whitelist[user_id_str]
            self.db.set("SubChecker", "whitelist", self.whitelist)
            return True
        return False

    async def save_not_subscribed_msg(self, user_id, message_id):
        """Сохранение ID сообщения о неподписке"""
        self.not_subscribed_msgs[str(user_id)] = message_id
        self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)

    async def delete_not_subscribed_msg(self, user_id):
        """Удаление сообщения о неподписке"""
        user_id_str = str(user_id)
        if user_id_str in self.not_subscribed_msgs:
            try:
                await self.client.delete_messages(user_id, self.not_subscribed_msgs[user_id_str])
            except Exception as e:
                print(f"Ошибка удаления сообщения: {e}")
            del self.not_subscribed_msgs[user_id_str]
            self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)

    async def pin_message(self, user_id, message_id):
        """Закрепление сообщения без уведомления"""
        if self.config["pin_enabled"]:
            try:
                await self.client(UpdatePinnedMessageRequest(
                    peer=user_id,
                    id=message_id,
                    silent=True,  # Без уведомления
                    unpin=False
                ))
                
                # Удаляем системное уведомление о закреплении
                await asyncio.sleep(1)
                async for message in self.client.iter_messages(user_id, limit=10):
                    if message.action and hasattr(message.action, '_name') and 'PinMessage' in message.action._name:
                        try:
                            await message.delete()
                            break
                        except:
                            pass
                            
            except Exception as e:
                print(f"Ошибка при закреплении сообщения: {e}")

    def get_not_subscribed_message(self):
        """Получение сообщения о неподписке"""
        custom_message = self.config["custom_message"]
        if custom_message:
            channel_link = self.config["channel_link"]
            channel_username = self.config["channel_username"]
            
            if channel_link:
                channel_display = f'<a href="{channel_link}">{channel_username or "наш канал"}</a>'
            else:
                channel_display = channel_username or "наш канал"
                
            return custom_message.replace("{channel_link}", channel_display)
        
        # Стандартное сообщение
        channel_link = self.config["channel_link"]
        channel_username = self.config["channel_username"]
        
        if channel_link:
            channel_display = f'<a href="{channel_link}">{channel_username or "наш канал"}</a>'
        else:
            channel_display = channel_username or "наш канал"
        
        return self.strings['not_subscribed'].format(channel_link=channel_display)

    @loader.command()
    async def subwl(self, message):
        """Управление белым списком"""
        args = utils.get_args_raw(message)
        
        if not args:
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
                await utils.answer(message, "<b>Укажите ID или ответьте на сообщение!</b>")
                return
            
            if self.is_whitelisted(user_id):
                await utils.answer(message, f"<b>Пользователь уже в белом списке!</b>\n\nID: <code>{user_id}</code>")
                return
            
            self.add_to_whitelist(user_id, message.sender_id)
            await utils.answer(message, self.strings['whitelist_added'].format(user_id))
            
            # Удаляем сообщение о подписке если есть
            if str(user_id) in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)
                await message.respond(f"<b>Пользователь добавлен в белый список!</b>\n\nID: <code>{user_id}</code>")
        
        elif command == "remove":
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
                await utils.answer(message, "<b>Укажите ID или ответьте на сообщение!</b>")
                return
            
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
            
            for user_id_str, data in list(self.whitelist.items())[:20]:  # Ограничение вывода
                try:
                    user_id = int(user_id_str)
                    user_info = f"<b>ID:</b> <code>{user_id}</code>\n"
                    user_info += f"<b>Добавлен:</b> {data.get('added_at', 'Неизвестно')}\n"
                    
                    try:
                        user = await self.client.get_entity(user_id)
                        name = utils.escape_html(getattr(user, 'first_name', '') or '')
                        if getattr(user, 'last_name', ''):
                            name += f" {utils.escape_html(user.last_name)}"
                        if not name and getattr(user, 'username', ''):
                            name = f"@{utils.escape_html(user.username)}"
                        name = name or "Неизвестно"
                        user_info += f"<b>Имя:</b> {name}\n"
                    except:
                        pass
                    
                    text += user_info + "─" * 20 + "\n"
                    count += 1
                        
                except Exception:
                    continue
            
            text = self.strings['whitelist_list'].format(f"Всего: {len(self.whitelist)}\n\n") + text
            await utils.answer(message, text)
        
        elif command == "clear":
            count = len(self.whitelist)
            self.whitelist.clear()
            self.db.set("SubChecker", "whitelist", self.whitelist)
            await utils.answer(message, self.strings['whitelist_cleared'].format(count))
        
        elif command == "check":
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
                await utils.answer(message, "<b>Укажите ID или ответьте на сообщение!</b>")
                return
            
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
        args = utils.get_args_raw(message).lower()
        
        if args == "on":
            self.config["pin_enabled"] = True
            status_text = "Включен"
            await utils.answer(message, self.strings['pinned_enabled'])
        elif args == "off":
            self.config["pin_enabled"] = False
            status_text = "Выключен"
            await utils.answer(message, self.strings['pinned_disabled'])
        else:
            status_text = "Включен" if self.config["pin_enabled"] else "Выключен"
            await utils.answer(message, self.strings['pinned_status'].format(status_text))

    @loader.command()
    async def submessage(self, message):
        """Кастомное сообщение, используйте {channel_link}"""
        args = utils.get_args_raw(message)
        
        if not args:
            if not self.config["custom_message"]:
                await utils.answer(message, self.strings['no_custom_message'])
            else:
                await utils.answer(message, 
                    self.strings['current_custom_message'].format(self.config["custom_message"])
                )
            return
        
        self.config["custom_message"] = args
        await utils.answer(message, self.strings['custom_message_set'])
    
    @loader.command()
    async def submessageclear(self, message):
        """Сбросить кастомное сообщение"""
        self.config["custom_message"] = ""
        await utils.answer(message, self.strings['custom_message_cleared'])

    @loader.command()
    async def subchannel(self, message):
        """Настроить канал для проверки подписки [юзернейм или ссылка]"""
        args = utils.get_args_raw(message)
        
        if not args:
            channel_username = self.config["channel_username"]
            if not channel_username:
                await utils.answer(message, self.strings['channel_not_set'])
            else:
                channel_info = f"@{channel_username}" if not channel_username.startswith('@') else channel_username
                channel_link = self.config["channel_link"]
                if channel_link:
                    channel_info = f"<a href='{channel_link}'>{channel_info}</a>"
                
                await utils.answer(message, 
                    self.strings['current_channel'].format(
                        channel_info, 
                        self.config["channel_id"] or "Не определен"
                    )
                )
            return
        
        # Очистка аргументов
        if args.startswith('@'):
            args = args[1:]
        
        if 't.me/' in args:
            if args.startswith('https://'):
                args = args.replace('https://t.me/', '')
            elif args.startswith('t.me/'):
                args = args.replace('t.me/', '')
        
        try:
            channel = await self.client.get_entity(args)
            
            self.config["channel_username"] = channel.username if hasattr(channel, 'username') else args
            self.config["channel_id"] = channel.id
            
            if hasattr(channel, 'username') and channel.username:
                self.config["channel_link"] = f"https://t.me/{channel.username}"
            else:
                self.config["channel_link"] = f"tg://resolve?domain={args}"
            
            channel_display = f"@{channel.username}" if hasattr(channel, 'username') else args
            channel_info = f"<a href='{self.config['channel_link']}'>{channel_display}</a>"
            
            await utils.answer(message, self.strings['channel_set'].format(channel_info))
            
        except Exception as e:
            await utils.answer(message, 
                self.strings['invalid_channel'] + f"\n\n<code>{utils.escape_html(str(e))}</code>"
            )

    @loader.command()
    async def subtest(self, message):
        """Протестировать доступ к каналу"""
        channel_id = self.config["channel_id"]
        if not channel_id:
            await utils.answer(message, self.strings['channel_not_set'])
            return
        
        try:
            channel = await self.client.get_entity(channel_id)
            
            # Быстрая проверка
            async for _ in self.client.iter_participants(channel_id, limit=1):
                pass
            
            channel_info = []
            if hasattr(channel, 'title'):
                channel_info.append(f"<b>Название:</b> {utils.escape_html(channel.title)}")
            if hasattr(channel, 'username'):
                channel_info.append(f"<b>Юзернейм:</b> @{channel.username}")
            channel_info.append(f"<b>ID:</b> <code>{channel.id}</code>")
            
            await utils.answer(message, 
                self.strings['test_success'] + "\n\n" + "\n".join(channel_info)
            )
            
        except Exception as e:
            error_msg = str(e)
            if "CHANNEL_PRIVATE" in error_msg or "аналог is private" in error_msg.lower():
                error_msg = self.strings['no_permission']
            
            await utils.answer(message, 
                self.strings['test_failed'].format(utils.escape_html(error_msg))
            )

    @loader.command()
    async def subcheck(self, message):
        """Включить/выключить проверку подписки"""
        args = utils.get_args_raw(message).lower()
        
        if args == "on":
            if not self.config["channel_id"]:
                await utils.answer(message, self.strings['channel_not_set'])
                return
                
            self.config["enabled"] = True
        elif args == "off":
            self.config["enabled"] = False
        
        status_text = "Включена" if self.config["enabled"] else "Выключена"
        channel_status = "Настроен" if self.config["channel_id"] else "Не настроен"
        pin_status = "Включен" if self.config["pin_enabled"] else "Выключен"
        whitelist_status = f"{len(self.whitelist)} пользователей"
        
        response = "<b>Статус проверки подписки:</b>\n\n"
        response += f"<b>Проверка:</b> {status_text}\n"
        response += f"<b>Канал:</b> {channel_status}\n"
        response += f"<b>Закреп сообщений:</b> {pin_status}\n"
        response += f"<b>Белый список:</b> {whitelist_status}\n"
        
        if self.config["channel_username"]:
            response += f"<b>Текущий канал:</b> {self.config['channel_username']}\n"
        
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
        if not self.config["enabled"]:
            return
        
        # Проверка настроен ли канал
        if not self.config["channel_id"]:
            return
            
        # Проверка что сообщение в личке и не исходящее
        if not message.is_private or message.out:
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
            user_id_str = str(user_id)
            if user_id_str in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)
                await message.respond(self.strings['subscribed'])
            return
        
        # Если не подписан
        user_id_str = str(user_id)
        if user_id_str not in self.not_subscribed_msgs:
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
        
        for user_id_str in list(self.not_subscribed_msgs.keys())[:50]:  # Ограничим вывод
            user_id = int(user_id_str)
            try:
                user = await self.client.get_entity(user_id)
                name = utils.escape_html(getattr(user, 'first_name', '') or '')
                if getattr(user, 'last_name', ''):
                    name += f" {utils.escape_html(user.last_name)}"
                if not name and getattr(user, 'username', ''):
                    name = f"@{utils.escape_html(user.username)}"
                name = name or str(user_id)
                
                is_subscribed = await self.check_subscription(user_id)
                sub_status = "✓ Подписан" if is_subscribed else "✗ Не подписан"
                whitelist_status = "✓ В белом списке" if self.is_whitelisted(user_id) else "✗ Не в белом списке"
                
                text += f"{name} (ID: {user_id})\n{sub_status} | {whitelist_status}\n"
                count += 1
            except:
                text += f"ID: {user_id}\n"
                count += 1
        
        text += f"\n<b>Всего:</b> {count}"
        if len(self.not_subscribed_msgs) > 50:
            text += f" (показано 50 из {len(self.not_subscribed_msgs)})"
        
        await utils.answer(message, text)

    @loader.command()
    async def subclean(self, message):
        """Очистить все сообщения о подписке"""
        count = 0
        tasks = []
        
        for user_id_str, msg_id in list(self.not_subscribed_msgs.items()):
            try:
                user_id = int(user_id_str)
                task = self.client.delete_messages(user_id, msg_id)
                tasks.append(task)
                count += 1
            except:
                continue
        
        # Асинхронное удаление
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.not_subscribed_msgs.clear()
        self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)
        
        await utils.answer(message, f"<b>Удалено {count} сообщений о подписке</b>")
