














# # class ImageUploadView(APIView):
# #     permission_classes = [AllowAny]
# #     serializer_class = ImageUploadSerializer

# #     def post(self, request):
# #         # 1) تحقق من وجود الصورة
# #         if 'image' not in request.FILES:
# #             return Response({'error': 'No image provided'}, status=400)

# #         # 2) احفظ الصورة مؤقتًا
# #         image = request.FILES['image']
# #         file_name = default_storage.save(f'uploads/{image.name}', image)
# #         image_path = default_storage.path(file_name)

# #         try:
# #             # 3) إعداد مسارات النموذج وخريطة التسميات
# #             model_dir = os.path.join(settings.MEDIA_ROOT, 'models')
# #             model_path = os.path.join(model_dir, 'product_model.h5')
# #             label_path = os.path.join(model_dir, 'label_map.pkl')

# #             if not os.path.exists(model_path):
# #                 return Response({'error': 'Model not trained yet'}, status=503)

# #             # 4) تحميل النموذج وخريطة التسميات
# #             model = load_model(model_path)
# #             with open(label_path, 'rb') as f:
# #                 label_map = pickle.load(f)

# #             # 5) بناء موديل لاستخراج الميزات (الطبقة Dense قبل softmax)
# #             feature_extractor = Model(
# #                 inputs=model.input,
# #                 outputs=model.layers[-3].output  # الطبقة: Dense(1024, relu)
# #             )

# #             # 6) قراءة الصورة وتجهيزها
# #             img = Image.open(image_path).convert('RGB').resize((224, 224))
# #             img_array = np.array(img) / 255.0
# #             img_array = np.expand_dims(img_array, axis=0)

# #             # 7) التنبؤ بالفئة الأساسية
# #             predictions = model.predict(img_array)[0]
# #             top_index = np.argmax(predictions)
# #             label_name = next(name for name, idx in label_map.items() if idx == top_index)

# #             # 8) استخراج متجه الميزات للصورة الجديدة
# #             features_query = feature_extractor.predict(img_array)[0]

# #             # 9) جلب المنتجات المطابقة للاسم
# #             ProductDetail = apps.get_model('exp1', 'ProductDetail')
# #             # matched_products = ProductDetail.objects.filter(name=label_name)
# #             matched_products = [
# #     product for product in ProductDetail.objects.all()
# #     if len(product.name.split('-')) > 1 and product.name.split('-')[0] == label_name
# # ]

# #             # 10) حساب التشابه مع كل منتج
# #             product_data = []
# #             for product in matched_products:
# #                 try:
# #                     db_img = Image.open(product.image.path).convert('RGB').resize((224, 224))
# #                     db_arr = np.array(db_img) / 255.0
# #                     db_arr = np.expand_dims(db_arr, axis=0)

# #                     db_feat = feature_extractor.predict(db_arr)[0]
# #                     similarity = float(cosine_similarity([features_query], [db_feat])[0][0])

# #                     product_data.append({
# #                     'name': product.name,
# #                     'price': product.price,
# #                     'image': request.build_absolute_uri(product.image.url),  # إضافة رابط الصورة
# #                     'content':product.content,
# #                     'description': product.description,
# #                     "product_type":product.product_type.name,
# #                     'company_name': product.product_type.company.name,
# #                     'similarity': similarity,
# #                     })
# #                 except Exception:
# #                     continue  # تجاهل أي صورة بها مشكلة

# #             # 11) ترتيب النتائج حسب التشابه
# #             product_data.sort(key=lambda x: x['similarity'], reverse=True)

# #             # 12) إرجاع النتيجة
# #             return Response({
# #                 'status': 'success',
# #                 'predicted_class': label_name,
# #                 'products': product_data
# #             })

# #         except Exception as e:
# #             return Response({'error': str(e)}, status=500)

# ==========================================================
# 📦 IMPORTS
# ==========================================================



from datetime import datetime
import stripe

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.core.files.storage import default_storage

from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication

# ==========================================================
# 🧩 LOCAL IMPORTS
# ==========================================================
from exp1.permision import IsSuperUser
from .models import (
    Profile, Cart, CartItem, Company, ProductType,
    ProductDetail, Order, OrderItem, ChatRoom, Message
)
from .ser import (
    LogoutSerializer, RegisterSerializer, LoginSerializer, ProfileSerializer,
    CompanySerializer, ProductTypeSerializer, ProductDetailSerializer,
    Cartserializer, AddCartItemSerializer, OrderSerializer, CreateOrderSerializer,
    ProductDetailSerializerput, UserSerializer,
    ChatRoomSerializer, MessageSerializer
)

# ==========================================================
# 💳 STRIPE CONFIG
# ==========================================================
stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()

# ==========================================================
# 🔐 AUTH HELPERS
# ==========================================================
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def initiate_payment(amount, email, order_id):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Supa Electronics Store',
                        'description': 'Best store in town',
                    },
                    'unit_amount': int(amount * 100),
                },
                'quantity': 1,
            }],
            metadata={'order_id': order_id},
            customer_email=email,
            mode='payment',
            success_url=f'http://127.0.0.1:8000/api/orders/{order_id}/success_payment/',
        )
        return Response({'session_url': session.url})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

# ==========================================================
# 📄 PAGINATION
# ==========================================================
class TenMessagePagination(PageNumberPagination):
    page_size = 100000000
    page_size_query_param = 'page_size'
    max_page_size = 50

# ==========================================================
# 👤 AUTH VIEWSETS
# ==========================================================
class RegisterViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(get_tokens_for_user(user), status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginRequestOTPView(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            return Response({"detail": "OTP sent to your email"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def list(self, request):
        return Response({"detail": "Use POST to request an OTP"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        try:
            user = User.objects.get(email=email)
            if user.verify_otp(otp):
                token = get_tokens_for_user(user)
                return Response(token, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class LogoutViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = LogoutSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh_token = serializer.validated_data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

class CurrentUserAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_superuser": user.is_superuser,
            "is_staff": user.is_staff,
        })

# ==========================================================
# 🏢 COMPANY / PRODUCT VIEWSETS
# ==========================================================
class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    pagination_class = TenMessagePagination

    def get_permissions(self):
        if self.action == 'create':
            return [IsSuperUser()]
        return [IsAuthenticatedOrReadOnly()]

class ProductTypeViewSet(viewsets.ModelViewSet):
    queryset = ProductType.objects.select_related('company').all()
    serializer_class = ProductTypeSerializer
    pagination_class = TenMessagePagination

    def get_permissions(self):
        if self.action == 'create':
            return [IsSuperUser()]
        return [IsAuthenticatedOrReadOnly()]

class ProductDetailViewSet(viewsets.ModelViewSet):
    queryset = ProductDetail.objects.select_related('product_type', 'product_type__company').all()
    serializer_class = ProductDetailSerializer
    pagination_class = TenMessagePagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'id']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperUser()]
        return [IsAuthenticatedOrReadOnly()]

class ProductDetailViewSetput(ProductDetailViewSet):
    serializer_class = ProductDetailSerializerput

# ==========================================================
# 👨‍💼 USER MANAGEMENT
# ==========================================================
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperUser]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = TenMessagePagination

    def create(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(get_tokens_for_user(user), status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==========================================================
# 🛒 CART MANAGEMENT
# ==========================================================
class CartViewSet(viewsets.ModelViewSet):
    serializer_class = Cartserializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = TenMessagePagination

    def get_queryset(self):
        user = self.request.user
        qs = Cart.objects.prefetch_related('items__product').all()
        return qs if user.is_superuser else qs.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            raise serializers.ValidationError({"error": "User must be authenticated"})
        if not user.is_superuser and Cart.objects.filter(user=user).exists():
            raise serializers.ValidationError({"error": "You can only create one cart."})
        serializer.save(user=user)

    @action(detail=True, methods=['post'], url_path='updateitem/(?P<product_id>[^/.]+)')
    def update_item_quantity(self, request, pk=None, product_id=None):
        try:
            cart = self.get_object()
            quantity = int(request.data.get('quantity', 0))
            if quantity < 1:
                return Response({"detail": "❌ الكمية يجب أن تكون 1 أو أكثر."}, status=status.HTTP_400_BAD_REQUEST)
            # item = cart.items.get(product__id=product_id)
            item = cart.items.select_for_update().get(product__id=product_id)
            item.quantity = quantity
            item.save()
            return Response({"detail": "✅ تم تعديل الكمية بنجاح."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='removeitem/(?P<item_id>[^/.]+)')
    def remove_item(self, request, pk=None, item_id=None):
        try:
            cart = self.get_object()
            item = CartItem.objects.get(id=item_id, cart=cart)
            item.delete()
            return Response({"detail": "تم حذف العنصر من السلة."}, status=status.HTTP_204_NO_CONTENT)
        except CartItem.DoesNotExist:
            return Response({"detail": "العنصر غير موجود."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'], url_path='deletecart')
    def delete_cart(self, request, pk=None):
        try:
            cart = self.get_object()
            cart.items.all().delete()
            cart.delete()
            return Response({"detail": "تم حذف السلة بنجاح."}, status=status.HTTP_204_NO_CONTENT)
        except Cart.DoesNotExist:
            return Response({"detail": "السلة غير موجودة."}, status=status.HTTP_404_NOT_FOUND)

class CartItemViewSet(viewsets.ModelViewSet):
    pagination_class = TenMessagePagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.prefetch_related('items__product').filter(cartcode=self.kwargs['zain_pk'])

    def get_serializer_context(self):
        return {'cart_id': self.kwargs['zain_pk']}

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddCartItemSerializer
        return Cartserializer

# ==========================================================
# 💰 ORDER MANAGEMENT
# ==========================================================
class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = TenMessagePagination

    def get_queryset(self):
        qs = Order.objects.select_related('owner').prefetch_related('items__product').all()
        return qs if self.request.user.is_superuser else qs.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        return OrderSerializer

    def get_serializer_context(self):
        return {'user_id': self.request.user.id}

    @action(detail=True, methods=['POST'])
    def pay(self, request, pk):
        order = self.get_object()
        return initiate_payment(order.total_price, request.user.email, str(order.id))

    @action(detail=True, methods=['GET'], permission_classes=[AllowAny])
    def success_payment(self, request, pk=None):
        order = get_object_or_404(Order, id=pk)
        order.pending_status = 'C'
        order.complete_at = datetime.now()
        order.save()
        return redirect('http://localhost:3000/orders')

# ==========================================================
# 💬 CHAT SYSTEM
# ==========================================================
class ChatRoomList(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TenMessagePagination

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class MessageList(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TenMessagePagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        roomname = self.kwargs.get('roomname')
        user = self.request.user
        if roomname:
            unread_messages = Message.objects.filter(room__name=roomname, is_read=False).exclude(sender=user)
            unread_messages.update(is_read=True)
            return Message.objects.select_related('sender', 'room').filter(room__name=roomname).order_by('timestamp')
        return Message.objects.none()

    @action(detail=False, methods=['get'])
    def room_messages(self, request, *args, **kwargs):
        roomname = self.kwargs.get('roomname')
        if not roomname:
            return Response({"detail": "Roomname not provided"}, status=400)
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_message(self, request, pk=None):
        try:
            message = Message.objects.get(pk=pk)
            if message.sender != request.user:
                return Response({"detail": "لا يمكنك حذف رسالة لم ترسلها."}, status=403)
            message.delete()
            return Response({"detail": "تم حذف الرسالة بنجاح."}, status=204)
        except Message.DoesNotExist:
            return Response({"detail": "الرسالة غير موجودة."}, status=404)

# ==========================================================
# 🧍 PROFILE VIEWSET
# ==========================================================
class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user').all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
