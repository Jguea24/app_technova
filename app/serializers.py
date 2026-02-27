from rest_framework import serializers
from django.contrib.auth.models import Group, User
from .models import (
    Banner,
    Category,
    Product,
    Cart,
    UserProfile,
    DeliveryAddress,
    RoleChangeRequest,
    Order,
    OrderItem,
    Shipment,
    ShipmentLocation,
)


# =====================================================
# SERIALIZER DE REGISTRO DE USUARIO (SIN ROLES)
# =====================================================

class RegisterSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role_reason = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'full_name',
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'username',
            'role',
            'role_reason',
            'password',
            'password2',
        ]
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

        if 'first_name' not in raw_data and 'nombre' in data:
            raw_data['first_name'] = data.get('first_name') or data.get('nombre')

        if 'last_name' not in raw_data and 'apellido' in data:
            raw_data['last_name'] = data.get('last_name') or data.get('apellido')

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

        if 'role' not in raw_data:
            raw_data['role'] = (
                data.get('role')
                or data.get('requested_role')
                or data.get('user_role')
                or ''
            )

        if 'role_reason' not in raw_data:
            raw_data['role_reason'] = (
                data.get('role_reason')
                or data.get('reason')
                or data.get('motivo')
                or ''
            )

        return super().to_internal_value(raw_data)

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        email = (attrs.get('email') or '').strip().lower()
        username = (attrs.get('username') or '').strip()
        phone = (attrs.get('phone') or '').strip()
        role = (attrs.get('role') or '').strip().lower()

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

        role_map = {
            'cliente': 'client',
            'client': 'client',
            'customer': 'client',
            'usuario': 'client',
            'user': 'client',
            'repartidor': 'driver',
            'driver': 'driver',
            'proveedor': 'provider',
            'provider': 'provider',
        }
        normalized_role = role_map.get(role, role)
        if normalized_role and normalized_role not in {'client', 'driver', 'provider'}:
            raise serializers.ValidationError({'role': 'Rol invalido. Usa client, driver o provider.'})

        attrs['email'] = email
        attrs['phone'] = phone
        attrs['role'] = normalized_role
        return attrs

    def create(self, validated_data):
        full_name = (validated_data.pop('full_name', '') or '').strip()
        first_name = (validated_data.pop('first_name', '') or '').strip()
        last_name = (validated_data.pop('last_name', '') or '').strip()
        phone = (validated_data.pop('phone', '') or '').strip()
        address = (validated_data.pop('address', '') or '').strip()
        requested_role = validated_data.pop('role', '')
        role_reason = (validated_data.pop('role_reason', '') or '').strip()
        validated_data.pop('password2', None)

        if full_name:
            name_parts = full_name.split(maxsplit=1)
            if not first_name:
                first_name = name_parts[0]
            if not last_name and len(name_parts) > 1:
                last_name = name_parts[1]

        if first_name:
            validated_data['first_name'] = first_name
        if last_name:
            validated_data['last_name'] = last_name

        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'phone': phone,
                'address': address,
            }
        )

        # Rol base para todas las cuentas.
        cliente_group, _ = Group.objects.get_or_create(name='CLIENTE')
        user.groups.add(cliente_group)

        # Para roles operativos, crea solicitud pendiente en registro.
        if requested_role in {'driver', 'provider'}:
            RoleChangeRequest.objects.create(
                user=user,
                requested_role=requested_role,
                reason=role_reason or 'Solicitud creada durante el registro.',
                status='pending',
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


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(read_only=True)
    product_image_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_price',
            'quantity',
            'subtotal',
            'product_image_url',
        ]
        read_only_fields = fields

    def get_product_image_url(self, obj):
        if not obj.product or not obj.product.image:
            return ''
        request = self.context.get('request')
        if request is None:
            return obj.product.image.url
        return request.build_absolute_uri(obj.product.image.url)


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'delivery_address',
            'delivery_main_address',
            'delivery_secondary_street',
            'delivery_apartment',
            'delivery_city',
            'delivery_instructions',
            'status',
            'status_label',
            'total_amount',
            'total_items',
            'created_at',
            'updated_at',
            'items',
        ]
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    delivery_address = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryAddress.objects.all(),
        required=False,
        allow_null=True,
    )

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)
        if 'delivery_address' not in raw_data:
            raw_data['delivery_address'] = (
                data.get('delivery_address')
                or data.get('address_id')
                or data.get('address')
                or data.get('direccion_id')
            )
        return super().to_internal_value(raw_data)


class ShipmentLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentLocation
        fields = ['id', 'latitude', 'longitude', 'heading', 'speed', 'recorded_at']
        read_only_fields = fields


class ShipmentSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(read_only=True)
    driver = serializers.PrimaryKeyRelatedField(read_only=True)
    driver_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    locations = serializers.SerializerMethodField()
    has_live_location = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            'id',
            'order',
            'driver',
            'driver_name',
            'status',
            'status_label',
            'current_latitude',
            'current_longitude',
            'current_heading',
            'current_speed',
            'last_location_at',
            'eta_minutes',
            'notes',
            'created_at',
            'updated_at',
            'has_live_location',
            'locations',
        ]
        read_only_fields = fields

    def get_driver_name(self, obj):
        if not obj.driver:
            return ''
        full_name = f'{obj.driver.first_name} {obj.driver.last_name}'.strip()
        return full_name or obj.driver.username

    def get_has_live_location(self, obj):
        return obj.current_latitude is not None and obj.current_longitude is not None

    def get_locations(self, obj):
        request = self.context.get('request')
        try:
            raw_limit = request.query_params.get('points', 60) if request else 60
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = 60
        limit = max(1, min(limit, 300))
        qs = obj.locations.all().order_by('-recorded_at', '-id')[:limit]
        return ShipmentLocationSerializer(qs, many=True).data


class ShipmentLocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    heading = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    speed = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Shipment.STATUS_CHOICES, required=False)
    eta_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)

        if 'latitude' not in raw_data:
            raw_data['latitude'] = data.get('lat') or data.get('current_latitude')

        if 'longitude' not in raw_data:
            raw_data['longitude'] = data.get('lng') or data.get('lon') or data.get('current_longitude')

        if 'eta_minutes' not in raw_data:
            raw_data['eta_minutes'] = (
                data.get('eta_minutes')
                or data.get('eta')
                or data.get('eta_min')
            )

        return super().to_internal_value(raw_data)

    def validate_latitude(self, value):
        if value < -90 or value > 90:
            raise serializers.ValidationError('latitude debe estar entre -90 y 90.')
        return value

    def validate_longitude(self, value):
        if value < -180 or value > 180:
            raise serializers.ValidationError('longitude debe estar entre -180 y 180.')
        return value


class ShipmentAssignDriverSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField(required=False, allow_null=True)
    auto_assign = serializers.BooleanField(required=False)

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)

        if 'driver_id' not in raw_data:
            raw_data['driver_id'] = (
                data.get('driver_id')
                or data.get('driver')
                or data.get('repartidor_id')
            )

        if 'auto_assign' not in raw_data:
            raw_data['auto_assign'] = (
                data.get('auto_assign')
                if data.get('auto_assign') is not None
                else data.get('autoAssign')
            )

        return super().to_internal_value(raw_data)

    def validate_driver_id(self, value):
        if value is None:
            return None

        exists = User.objects.filter(id=value, is_active=True).exists()
        if not exists:
            raise serializers.ValidationError('El repartidor no existe o esta inactivo.')

        return value

    def validate(self, attrs):
        has_driver_id = 'driver_id' in attrs
        auto_assign = attrs.get('auto_assign')

        if has_driver_id and auto_assign:
            raise serializers.ValidationError(
                {'non_field_errors': 'No envies driver_id y auto_assign=true al mismo tiempo.'}
            )

        return attrs


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
    role = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    pending_role_request = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'address',
            'role',
            'roles',
            'pending_role_request',
        ]
        read_only_fields = ['id', 'username', 'role', 'roles', 'pending_role_request']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['full_name'] = f'{instance.first_name} {instance.last_name}'.strip()
        data['phone'] = getattr(getattr(instance, 'profile', None), 'phone', '')
        data['address'] = getattr(getattr(instance, 'profile', None), 'address', '')
        return data

    def _resolve_primary_role(self, roles):
        role_set = set(roles)
        if 'ADMIN' in role_set:
            return 'admin'
        if 'DRIVER' in role_set or 'REPARTIDOR' in role_set:
            return 'driver'
        if 'PROVIDER' in role_set:
            return 'provider'
        if 'CLIENTE' in role_set:
            return 'client'
        return 'user'

    def get_roles(self, instance):
        return sorted(list(instance.groups.values_list('name', flat=True)))

    def get_role(self, instance):
        roles = self.get_roles(instance)
        return self._resolve_primary_role(roles)

    def get_pending_role_request(self, instance):
        pending = instance.role_change_requests.filter(status='pending').order_by('-id').first()
        if not pending:
            return None
        return {
            'id': pending.id,
            'requested_role': pending.requested_role,
            'status': pending.status,
            'reason': pending.reason,
            'created_at': pending.created_at,
        }

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)

        if 'full_name' not in raw_data and (
            'name' in data or 'nombre' in data or 'fullName' in data
        ):
            raw_data['full_name'] = (
                data.get('full_name')
                or data.get('name')
                or data.get('nombre')
                or data.get('fullName')
            )

        if 'first_name' not in raw_data and 'nombre' in data:
            raw_data['first_name'] = (
                data.get('first_name')
                or data.get('nombre')
            )

        if 'last_name' not in raw_data and 'apellido' in data:
            raw_data['last_name'] = (
                data.get('last_name')
                or data.get('apellido')
            )

        if 'phone' not in raw_data and ('telefono' in data or 'celular' in data):
            raw_data['phone'] = (
                data.get('phone')
                or data.get('telefono')
                or data.get('celular')
            )

        if 'address' not in raw_data and 'direccion' in data:
            raw_data['address'] = (
                data.get('address')
                or data.get('direccion')
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
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        phone = validated_data.pop('phone', None)
        address = validated_data.pop('address', None)

        if 'email' in validated_data:
            instance.email = validated_data['email']

        if full_name is not None:
            full_name = full_name.strip()
            name_parts = full_name.split(maxsplit=1) if full_name else []
            instance.first_name = name_parts[0] if len(name_parts) > 0 else ''
            instance.last_name = name_parts[1] if len(name_parts) > 1 else ''
        else:
            if first_name is not None:
                instance.first_name = (first_name or '').strip()
            if last_name is not None:
                instance.last_name = (last_name or '').strip()

        instance.save()

        if phone is not None or address is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            if phone is not None:
                profile.phone = phone.strip()
            if address is not None:
                profile.address = (address or '').strip()
            profile.save()

        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_staff',
            'role',
            'roles',
            'phone',
            'address',
        ]
        read_only_fields = ['id', 'roles']

    def _resolve_primary_role(self, roles):
        role_set = set(roles)
        if 'ADMIN' in role_set:
            return 'admin'
        if 'DRIVER' in role_set or 'REPARTIDOR' in role_set:
            return 'driver'
        if 'PROVIDER' in role_set:
            return 'provider'
        if 'CLIENTE' in role_set:
            return 'client'
        return 'user'

    def get_roles(self, instance):
        return sorted(list(instance.groups.values_list('name', flat=True)))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['phone'] = getattr(getattr(instance, 'profile', None), 'phone', '')
        data['address'] = getattr(getattr(instance, 'profile', None), 'address', '')
        data['role'] = self._resolve_primary_role(self.get_roles(instance))
        return data

    def to_internal_value(self, data):
        raw_data = data.copy() if hasattr(data, 'copy') else dict(data)

        if 'first_name' not in raw_data and 'nombre' in data:
            raw_data['first_name'] = (
                data.get('first_name')
                or data.get('nombre')
            )

        if 'last_name' not in raw_data and 'apellido' in data:
            raw_data['last_name'] = (
                data.get('last_name')
                or data.get('apellido')
            )

        if 'phone' not in raw_data and ('telefono' in data or 'celular' in data):
            raw_data['phone'] = (
                data.get('phone')
                or data.get('telefono')
                or data.get('celular')
            )

        if 'address' not in raw_data and 'direccion' in data:
            raw_data['address'] = (
                data.get('address')
                or data.get('direccion')
            )

        if 'role' not in raw_data and (
            'rol' in data or 'requested_role' in data or 'user_role' in data
        ):
            raw_data['role'] = (
                data.get('role')
                or data.get('rol')
                or data.get('requested_role')
                or data.get('user_role')
            )

        if 'is_staff' not in raw_data:
            if 'staff' in data:
                raw_data['is_staff'] = data.get('staff')
            elif 'es_staff' in data:
                raw_data['is_staff'] = data.get('es_staff')

        return super().to_internal_value(raw_data)

    def validate_email(self, value):
        email = (value or '').strip().lower()
        user = self.instance
        if User.objects.filter(email=email).exclude(id=user.id).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return email

    def validate_username(self, value):
        username = (value or '').strip()
        user = self.instance
        if User.objects.filter(username=username).exclude(id=user.id).exists():
            raise serializers.ValidationError('Este usuario ya existe.')
        return username

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

    def validate_role(self, value):
        role = (value or '').strip().lower()
        if not role:
            return ''
        role_map = {
            'cliente': 'client',
            'client': 'client',
            'customer': 'client',
            'usuario': 'client',
            'user': 'client',
            'repartidor': 'driver',
            'driver': 'driver',
            'proveedor': 'provider',
            'provider': 'provider',
            'admin': 'admin',
            'administrador': 'admin',
        }
        normalized = role_map.get(role, role)
        if normalized not in {'client', 'driver', 'provider', 'admin'}:
            raise serializers.ValidationError('Rol invalido. Usa client, driver, provider o admin.')
        return normalized

    def _apply_role(self, instance, role):
        if not role:
            return
        role_groups = {
            'client': ['CLIENTE'],
            'driver': ['CLIENTE', 'DRIVER'],
            'provider': ['CLIENTE', 'PROVIDER'],
            'admin': ['ADMIN', 'CLIENTE'],
        }
        target_names = role_groups.get(role, [])
        if not target_names:
            return

        known_role_names = {'CLIENTE', 'DRIVER', 'PROVIDER', 'ADMIN'}
        instance.groups.remove(*Group.objects.filter(name__in=known_role_names))

        for name in target_names:
            group, _ = Group.objects.get_or_create(name=name)
            instance.groups.add(group)

        if instance.is_superuser:
            instance.is_staff = True
        else:
            instance.is_staff = role == 'admin'
        instance.save(update_fields=['is_staff'])

    def update(self, instance, validated_data):
        phone = validated_data.pop('phone', None)
        address = validated_data.pop('address', None)
        role = validated_data.pop('role', None)

        if 'username' in validated_data:
            instance.username = validated_data['username']

        if 'email' in validated_data:
            instance.email = validated_data['email']

        if 'first_name' in validated_data:
            instance.first_name = (validated_data['first_name'] or '').strip()

        if 'last_name' in validated_data:
            instance.last_name = (validated_data['last_name'] or '').strip()

        if 'is_staff' in validated_data:
            instance.is_staff = validated_data['is_staff']

        instance.save()

        if phone is not None or address is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            if phone is not None:
                profile.phone = phone.strip()
            if address is not None:
                profile.address = (address or '').strip()
            profile.save()

        if role is not None:
            self._apply_role(instance, role)

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
