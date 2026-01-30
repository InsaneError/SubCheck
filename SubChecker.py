from telethon import events, Button
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telethon.tl.functions.messages import ReportSpamRequest
from telethon.tl.types import User
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
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
        'bot_detected': "<b>Бот обнаружен!</b>\n\nБоты не проходят проверку подписки.",
        'custom_message_set': "<b>Кастомное сообщение установлено!</b>",
        'custom_message_cleared': "<b>Кастомное сообщение сброшено!</b>",
        'current_custom_message': "<b>Текущее кастомное сообщение:</b>\n\n{}",
        'no_custom_message': "<b>Кастомное сообщение не установлено.</b>\nИспользуется стандартное сообщение.",
        'pinned_enabled': "<b>Закреп сообщений включен!</b>\nСообщения с просьбой подписаться будут закрепляться.",
        'pinned_disabled': "<b>Закреп сообщений отключен!</b>\nСообщения с просьбой подписаться не будут закрепляться.",
        'pinned_status': "<b>Статус закрепа сообщений:</b> {}"
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        
        self.channel_username = self.db.get("SubChecker", "channel_username", "")
        self.channel_link = self.db.get("SubChecker", "channel_link", "")
        self.channel_id = self.db.get("SubChecker", "channel_id", None)
        
        self.not_subscribed_msgs = self.db.get("SubChecker", "not_subscribed_msgs", {})
        
        self.custom_message = self.db.get("SubChecker", "custom_message", "")
        
        self.pin_enabled = self.db.get("SubChecker", "pin_enabled", True)

    async def check_subscription(self, user_id):
        if not self.channel_id:
            return False
        
        try:
            participants = await self.client.get_participants(self.channel_id, limit=10000)
           
            return any(participant.id == user_id for participant in participants)
        except Exception as e:
            print(f"Ошибка проверки подписки: {e}")
            return False

    def is_bot(self, user):
        if isinstance(user, User):
            return user.bot
        return False

    async def save_not_subscribed_msg(self, user_id, message_id):
        self.not_subscribed_msgs[str(user_id)] = message_id
        self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)

    async def delete_not_subscribed_msg(self, user_id):
        if str(user_id) in self.not_subscribed_msgs:
            try:
                # Открепляем сообщение перед удалением
                if self.pin_enabled:
                    try:
                        await self.client(UpdatePinnedMessageRequest(
                            peer=user_id,
                            id=self.not_subscribed_msgs[str(user_id)],
                            silent=True,
                            unpin=True  # Открепляем
                        ))
                        print(f"Сообщение откреплено для пользователя {user_id}")
                    except Exception as e:
                        print(f"Ошибка при откреплении сообщения: {e}")
                
                # Удаляем сообщение
                await self.client.delete_messages(user_id, self.not_subscribed_msgs[str(user_id)])
            except:
                pass
            del self.not_subscribed_msgs[str(user_id)]
            self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)

    async def pin_message(self, user_id, message_id):
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
            enabled = True
        elif args.lower() == "off":
            self.db.set("SubChecker", "enabled", False)
            enabled = False
        
        
        status_text = "Включена" if enabled else "Выключена"
        channel_status = "Настроен" if self.channel_id else "Не настроен"
        pin_status = "Включен" if self.pin_enabled else "Выключен"
        
        response = "<b>Статус проверки подписки:</b>\n\n"
        response += f"<b>Проверка:</b> {status_text}\n"
        response += f"<b>Канал:</b> {channel_status}\n"
        response += f"<b>Закреп сообщений:</b> {pin_status}\n"
        
        if self.channel_username:
            response += f"<b>Текущий канал:</b> {self.channel_username}\n"
        
        response += "\n<b>Команды:</b>\n"
        response += ".subcheck on - включить проверку\n"
        response += ".subcheck off - выключить проверку\n"
        response += ".subchannel @юзернейм - установить канал\n"
        response += ".submessage текст - установить кастомное сообщение\n"
        response += ".submessageclear - сбросить кастомное сообщение\n"
        response += ".subpin on/off - включить/выключить закреп сообщений"
        
        await utils.answer(message, response)

    async def watcher(self, message):
        
        if not self.db.get("SubChecker", "enabled", True):
            return
        
        
        if not self.channel_id:
            print("Канал не настроен")
            return
            
        
        if not message.is_private:
            return
            
        
        if message.out:
            return
        
        
        try:
            user = await message.get_sender()
        except:
            print("Не удалось получить информацию об отправителе")
            return
        
        
        if self.is_bot(user):
            print(f"Сообщение от бота {user.id}, игнорируем")
            return
        
        user_id = user.id
        
        
        is_subscribed = await self.check_subscription(user_id)
        
        
        if is_subscribed:
           
            if str(user_id) in self.not_subscribed_msgs:
                print(f"Пользователь {user_id} подписался, удаляем сообщение с просьбой подписаться")
                await self.delete_not_subscribed_msg(user_id)
                await message.respond(self.strings['subscribed'])
            return
        
       
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
                
                text += f"{name} (ID: {user_id}) - {sub_status}\n"
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
                # Открепляем сообщение перед удалением
                if self.pin_enabled:
                    try:
                        await self.client(UpdatePinnedMessageRequest(
                            peer=user_id,
                            id=self.not_subscribed_msgs[user_id_str],
                            silent=True,
                            unpin=True  # Открепляем
                        ))
                        print(f"Сообщение откреплено для пользователя {user_id}")
                    except Exception as e:
                        print(f"Ошибка при откреплении сообщения: {e}")
                
                # Удаляем сообщение
                await self.client.delete_messages(user_id, self.not_subscribed_msgs[user_id_str])
                count += 1
            except:
                pass
        
        self.not_subscribed_msgs = {}
        self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)
        
        await utils.answer(message, f"<b>Удалено {count} сообщений о подписке</b>")
