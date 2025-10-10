import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from erp_main.models import ChatRoom, ChatMessage, UserStatus


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        await self.update_user_status(True)

        # Присоединяемся к комнатам пользователя
        self.room_groups = []
        user_rooms = await self.get_user_rooms()

        for room in user_rooms:
            room_group_name = f'chat_{room.id}'
            self.room_groups.append(room_group_name)
            await self.channel_layer.group_add(
                room_group_name,
                self.channel_name
            )

        await self.accept()

    async def disconnect(self, close_code):
        await self.update_user_status(False)

        for room_group in self.room_groups:
            await self.channel_layer.group_discard(
                room_group,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'chat_message':
            await self.handle_chat_message(data)
        elif message_type == 'typing':
            await self.handle_typing_indicator(data)
        elif message_type == 'message_read':
            await self.handle_message_read(data)

    async def handle_chat_message(self, data):
        room_id = data['room_id']
        content = data['content']
        message_type = data.get('message_type', 'text')
        reply_to_id = data.get('reply_to')

        message = await self.create_message(room_id, content, message_type, reply_to_id)

        await self.channel_layer.group_send(
            f'chat_{room_id}',
            {
                'type': 'chat_message',
                'message': await self.serialize_message(message)
            }
        )

    async def handle_typing_indicator(self, data):
        room_id = data['room_id']
        is_typing = data['is_typing']

        await self.channel_layer.group_send(
            f'chat_{room_id}',
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'user_name': self.user.get_full_name() or self.user.username,
                'is_typing': is_typing
            }
        )

    async def handle_message_read(self, data):
        message_id = data['message_id']
        await self.mark_message_as_read(message_id)

        await self.channel_layer.group_send(
            f'chat_{data["room_id"]}',
            {
                'type': 'message_read',
                'message_id': message_id,
                'user_id': self.user.id
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'is_typing': event['is_typing']
        }))

    async def message_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'user_id': event['user_id']
        }))

    @database_sync_to_async
    def get_user_rooms(self):
        return list(ChatRoom.objects.filter(participants=self.user, is_active=True))

    @database_sync_to_async
    def create_message(self, room_id, content, message_type, reply_to_id):
        room = ChatRoom.objects.get(id=room_id)
        reply_to = None
        if reply_to_id:
            reply_to = ChatMessage.objects.get(id=reply_to_id)

        message = ChatMessage.objects.create(
            room=room,
            user=self.user,
            content=content,
            message_type=message_type,
            reply_to=reply_to
        )
        return message

    @database_sync_to_async
    def serialize_message(self, message):
        from erp_main.serializers import ChatMessageSerializer
        return ChatMessageSerializer(message).data

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        message = ChatMessage.objects.get(id=message_id)
        message.is_read = True
        message.save()

    @database_sync_to_async
    def update_user_status(self, is_online):
        status, created = UserStatus.objects.get_or_create(user=self.user)
        status.is_online = is_online
        status.save()