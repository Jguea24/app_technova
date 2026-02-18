from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Banner, Category, Product, Cart, UserProfile, DeliveryAddress, RoleChangeRequest


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
# SERIALIZER DE CATEGORIAS
# =====================================================

class CategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'order', 'image', 'image_url']

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        request = self.context.get('request')
        if request is None:
            return obj.image.url
        return request.build_absolute_uri(obj.image.url)


# =====================================================
# SERIALIZER DE BANNERS
# =====================================================

class BannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ['id', 'title', 'image', 'image_url', 'order']

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        request = self.context.get('request')
        if request is None:
            return obj.image.url
        return request.build_absolute_uri(obj.image.url)


# =====================================================
# SERIALIZER DE PRODUCTOS
# =====================================================

class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'price',
            'old_price',
            'description',
            'store_name',
            'rating',
            'reviews_count',
            'stock',
            'image',
            'image_url',
            'category',
            'category_name',
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        request = self.context.get('request')
        if request is None:
            return obj.image.url
        return request.build_absolute_uri(obj.image.url)


# =====================================================
# SERIALIZER DE CARRITO
# =====================================================

class CartSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(
        source='product.price',
        max_digits=8,
        decimal_places=2,
        read_only=True,
    )
    product_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id',
            'user',
            'product',
            'quantity',
            'product_name',
            'product_price',
            'product_image_url',
        ]
        read_only_fields = ['id', 'user', 'product_name', 'product_price', 'product_image_url']

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)

        if 'product' not in raw_data:
            raw_data['product'] = (
                data.get('product_id')
                or data.get('productId')
                or data.get('producto')
                or data.get('id_producto')
            )

        if 'quantity' not in raw_data:
            raw_data['quantity'] = (
                data.get('quantity')
                or data.get('cantidad')
                or data.get('qty')
                or 1
            )

        return super().to_internal_value(raw_data)

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError('La cantidad debe ser mayor a 0.')
        return value

    def get_product_image_url(self, obj):
        if not obj.product or not obj.product.image:
            return ''
        request = self.context.get('request')
        if request is None:
            return obj.product.image.url
        return request.build_absolute_uri(obj.product.image.url)


class DeliveryAddressSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = DeliveryAddress
        fields = [
            'id',
            'user',
            'main_address',
            'secondary_street',
            'apartment',
            'city',
            'delivery_instructions',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)

        if 'main_address' not in raw_data:
            raw_data['main_address'] = (
                data.get('direccion_principal')
                or data.get('direccionPrincipal')
                or data.get('address_line_1')
                or data.get('street')
                or ''
            )

        if 'secondary_street' not in raw_data:
            raw_data['secondary_street'] = (
                data.get('calle_secundaria')
                or data.get('calleSecundaria')
                or data.get('address_line_2')
                or ''
            )

        if 'apartment' not in raw_data:
            raw_data['apartment'] = (
                data.get('piso_departamento')
                or data.get('pisoDepartamento')
                or data.get('departamento')
                or ''
            )

        if 'city' not in raw_data:
            raw_data['city'] = (
                data.get('ciudad')
                or data.get('province')
                or data.get('provincia')
                or ''
            )

        if 'delivery_instructions' not in raw_data:
            raw_data['delivery_instructions'] = (
                data.get('indicaciones')
                or data.get('indicaciones_entrega')
                or data.get('reference')
                or data.get('notes')
                or ''
            )

        if 'is_default' not in raw_data:
            raw_data['is_default'] = (
                data.get('default')
                if data.get('default') is not None
                else data.get('isDefault', False)
            )

        return super().to_internal_value(raw_data)

    def validate_main_address(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('La direccion principal es obligatoria.')
        return value

    def validate_city(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('La ciudad es obligatoria.')
        return value


class MeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'phone', 'address']
        read_only_fields = ['id', 'username']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['full_name'] = f'{instance.first_name} {instance.last_name}'.strip()
        data['phone'] = getattr(getattr(instance, 'profile', None), 'phone', '')
        data['address'] = getattr(getattr(instance, 'profile', None), 'address', '')
        return data

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)

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

        return super().to_internal_value(raw_data)

    def validate_email(self, value):
        email = (value or '').strip().lower()
        user = self.instance
        if User.objects.filter(email=email).exclude(id=user.id).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return email

    def validate_phone(self, value):
        value = (value or '').strip()
        if not value:
            return value
        if not value.isdigit():
            raise serializers.ValidationError('El telefono solo debe contener numeros.')
        if len(value) != 10:
            raise serializers.ValidationError('El telefono debe tener exactamente 10 digitos.')
        if not value.startswith('09'):
            raise serializers.ValidationError('El telefono debe iniciar con 09.')
        return value

    def update(self, instance, validated_data):
        full_name = validated_data.pop('full_name', None)
        phone = validated_data.pop('phone', None)
        address = validated_data.pop('address', None)

        if 'email' in validated_data:
            instance.email = validated_data['email']

        if full_name is not None:
            full_name = full_name.strip()
            name_parts = full_name.split(maxsplit=1) if full_name else []
            instance.first_name = name_parts[0] if len(name_parts) > 0 else ''
            instance.last_name = name_parts[1] if len(name_parts) > 1 else ''

        instance.save()

        if phone is not None or address is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            if phone is not None:
                profile.phone = phone.strip()
            if address is not None:
                profile.address = (address or '').strip()
            profile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    new_password2 = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)

        if 'current_password' not in raw_data:
            raw_data['current_password'] = (
                data.get('current_password')
                or data.get('old_password')
                or data.get('actual_password')
                or ''
            )

        if 'new_password' not in raw_data:
            raw_data['new_password'] = (
                data.get('new_password')
                or data.get('password')
                or data.get('nueva_password')
                or ''
            )

        if 'new_password2' not in raw_data:
            raw_data['new_password2'] = (
                data.get('new_password2')
                or data.get('confirm_password')
                or data.get('confirmPassword')
                or ''
            )

        return super().to_internal_value(raw_data)

    def validate(self, attrs):
        new_password = attrs.get('new_password') or ''
        new_password2 = attrs.get('new_password2') or ''
        if len(new_password) < 8:
            raise serializers.ValidationError({'new_password': 'La nueva contrasena debe tener minimo 8 caracteres.'})
        if new_password2 and new_password != new_password2:
            raise serializers.ValidationError({'new_password2': 'Las contrasenas no coinciden.'})
        return attrs


class RoleChangeRequestSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = RoleChangeRequest
        fields = ['id', 'user', 'requested_role', 'reason', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'status', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)

        if 'requested_role' not in raw_data:
            raw_data['requested_role'] = (
                data.get('requested_role')
                or data.get('role')
                or data.get('nuevo_rol')
                or ''
            )

        role = (raw_data.get('requested_role') or '').strip().lower()
        role_map = {
            'proveedor': 'provider',
            'repartidor': 'driver',
            'provider': 'provider',
            'driver': 'driver',
        }
        if role:
            raw_data['requested_role'] = role_map.get(role, role)

        if 'reason' not in raw_data:
            raw_data['reason'] = (
                data.get('reason')
                or data.get('motivo')
                or data.get('description')
                or ''
            )

        return super().to_internal_value(raw_data)
