# import uuid
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.conf import settings
# from django.db import transaction
# from .models import Cart, Profile, ChatRoom


# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_user_profile(sender, instance, created, **kwargs):
#     cart = Cart.objects.filter(user=instance).first()
#     if not cart:
#         cart = Cart.objects.create(user=instance)
#     if created:
#         Profile.objects.create(user=instance)


# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_chat_room_for_new_user(sender, instance, created, **kwargs):
#     if created:
#         def create_room():
#             base_name =instance.email.split('@')[0] + str(uuid.uuid4())[:5]
#             room_name = base_name
#             counter = 1
#             while ChatRoom.objects.filter(name=room_name).exists():
#                 room_name = f"{base_name}-{counter}"
#                 counter += 1
#             ChatRoom.objects.create(user=instance, name=room_name)

#         transaction.on_commit(create_room)

import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.db import transaction
from .models import Cart, Profile, ChatRoom

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_related(sender, instance, created, **kwargs):
    """
    عند إنشاء مستخدم جديد:
    1- إنشاء Profile.
    2- إنشاء Cart إذا لم يكن موجودًا.
    3- إنشاء ChatRoom باسم فريد.
    """
    if created:
        # إنشاء Profile
        Profile.objects.create(user=instance)

        # إنشاء Cart إذا لم يكن موجودًا
        Cart.objects.get_or_create(user=instance)

        # إنشاء ChatRoom بعد التزام المعاملة
        def create_chat_room():
            base_name = instance.email.split('@')[0] + str(uuid.uuid4())[:5]
            room_name = base_name
            counter = 1
            # تحقق من التكرار
            while ChatRoom.objects.filter(name=room_name).exists():
                room_name = f"{base_name}-{counter}"
                counter += 1
            ChatRoom.objects.create(user=instance, name=room_name)

        transaction.on_commit(create_chat_room)
