from rest_framework import generics, permissions
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.exceptions import ObjectDoesNotExist

from .models import Product, Cart
from .serializers import ProductSerializer, CartSerializer, RegisterSerializer


# 🔐 REGISTER
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


# 🔐 LOGIN
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            user = User.objects.get(username=username)
            if not user.check_password(password):
                return Response({'error': 'Credenciales inválidas'}, status=400)

            refresh = RefreshToken.for_user(user)
            phone = ''
            address = ''
            try:
                phone = user.profile.phone
                address = user.profile.address
            except ObjectDoesNotExist:
                phone = ''
                address = ''

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': f'{user.first_name} {user.last_name}'.strip(),
                    'phone': phone,
                    'address': address
                }
            })

        except User.DoesNotExist:
            return Response({'error': 'Usuario no existe'}, status=400)


# 📦 PRODUCTOS
class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]


# 🛒 CARRITO
class CartView(generics.ListCreateAPIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
