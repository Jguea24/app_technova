from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Product, Cart, UserProfile


# =====================================================
# SERIALIZER DE REGISTRO DE USUARIO (SIN ROLES)
# =====================================================

class RegisterSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'address', 'username', 'password', 'password2']
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': False},
        }

    def to_internal_value(self, data):
        raw_data = data.copy()

        if 'full_name' not in raw_data:
            raw_data['full_name'] = (
                data.get('full_name')
                or data.get('name')
                or data.get('nombre')
                or data.get('fullName')
                or ''
            )

        if 'phone' not in raw_data:
            raw_data['phone'] = (
                data.get('phone')
                or data.get('telefono')
                or data.get('celular')
                or ''
            )

        if 'address' not in raw_data:
            raw_data['address'] = (
                data.get('address')
                or data.get('direccion')
                or ''
            )

        if 'username' not in raw_data:
            raw_data['username'] = (
                data.get('username')
                or data.get('usuario')
                or data.get('user')
                or ''
            )

        if 'password' not in raw_data:
            raw_data['password'] = data.get('password') or data.get('contrasena') or ''

        if 'password2' not in raw_data:
            raw_data['password2'] = (
                data.get('password2')
                or data.get('confirm_password')
                or data.get('confirmPassword')
                or data.get('password_confirmation')
                or ''
            )

        return super().to_internal_value(raw_data)

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        email = (attrs.get('email') or '').strip().lower()
        username = (attrs.get('username') or '').strip()
        phone = (attrs.get('phone') or '').strip()

        if not password:
            raise serializers.ValidationError({'password': 'Este campo es obligatorio.'})

        if password2 and password != password2:
            raise serializers.ValidationError({'password2': 'Las contrasenas no coinciden.'})

        if not phone:
            raise serializers.ValidationError({'phone': 'El telefono es obligatorio.'})

        if not phone.isdigit():
            raise serializers.ValidationError({'phone': 'El telefono solo debe contener numeros.'})

        if len(phone) != 10:
            raise serializers.ValidationError({'phone': 'El telefono debe tener exactamente 10 digitos.'})

        if not phone.startswith('09'):
            raise serializers.ValidationError({'phone': 'El telefono debe iniciar con 09.'})

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'Ya existe una cuenta con este correo.'})

        if not username:
            base_username = (email.split('@')[0] if email else 'usuario').replace(' ', '')
            username = base_username or 'usuario'
            suffix = 1
            candidate = username
            while User.objects.filter(username=candidate).exists():
                suffix += 1
                candidate = f'{username}{suffix}'
            attrs['username'] = candidate
        elif User.objects.filter(username=username).exists():
            raise serializers.ValidationError({'username': 'Este usuario ya existe.'})

        attrs['email'] = email
        attrs['phone'] = phone
        return attrs

    def create(self, validated_data):
        full_name = (validated_data.pop('full_name', '') or '').strip()
        phone = (validated_data.pop('phone', '') or '').strip()
        address = (validated_data.pop('address', '') or '').strip()
        validated_data.pop('password2', None)

        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        if full_name:
            name_parts = full_name.split(maxsplit=1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            user.save(update_fields=['first_name', 'last_name'])

        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'phone': phone,
                'address': address,
            }
        )

        return user


# =====================================================
# SERIALIZER DE PRODUCTOS
# =====================================================

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


# =====================================================
# SERIALIZER DE CARRITO
# =====================================================

class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'
