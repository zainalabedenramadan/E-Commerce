

from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .models import ChatRoom, Message, Profile
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os
import base64
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()
AES_KEY = b'12345678901234567890123456789012'  # مفتاح AES

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group = f'chat_{self.room_name}'

        # الحصول على غرفة الدردشة بشكل آمن
        self.room = await sync_to_async(ChatRoom.objects.select_related('user').get)(name=self.room_name)

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_content = data['message']
            access_token = data.get('user')
        except (json.JSONDecodeError, KeyError):
            await self.send(json.dumps({"error": "Invalid payload"}))
            return

        # التحقق من JWT
        try:
            token = AccessToken(access_token)
            user_id = token['user_id']
            user = await sync_to_async(User.objects.get)(id=user_id)
        except AuthenticationFailed:
            await self.send(json.dumps({"error": "فشل التوثيق"}))
            return
        except User.DoesNotExist:
            await self.send(json.dumps({"error": "المستخدم غير موجود"}))
            return

        # حفظ الرسالة
        await self.save_message(message_content, user)

        # إرسال الرسالة لجميع أعضاء الغرفة
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat_message",
                "message": message_content,
                "user_id": user.id
            }
        )

    async def chat_message(self, event):
        message = event['message']
        user_id = event.get('user_id')

        # الحصول على المستخدم وProfile مع تقليل الاستعلامات
        user = await sync_to_async(User.objects.select_related('profile').get)(id=user_id)
        sender_name = user.profile.full_name if hasattr(user, 'profile') and user.profile.full_name else user.email

        # حساب الرسائل الغير مقروءة للغرفة
        unread_count = await sync_to_async(lambda: self.room.messages.filter(is_read=False).exclude(sender=user).count())()

        await self.send(json.dumps({
            "message": message,
            "sender": user_id,
            "sender_name": sender_name,
            "room_name": self.room_name,
            "unread_count": unread_count
        }))

    @sync_to_async
    def save_message(self, message_content, user):
        encrypted = self.encrypt_message(message_content)
        Message.objects.create(room=self.room, content=encrypted, sender=user)

    def encrypt_message(self, message):
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(message.encode()) + padder.finalize()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(iv + encrypted_data).decode('utf-8')
