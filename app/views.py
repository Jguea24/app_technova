import json
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from django.contrib.auth.models import User
from django.db.models import Count, Min, Q, Sum
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Banner,
    Category,
    Product,
    Cart,
    DeliveryAddress,
    RoleChangeRequest,
    Order,
    OrderItem,
    Shipment,
    ShipmentLocation,
)
from .serializers import (
    BannerSerializer,
    CategorySerializer,
    ProductSerializer,
    CartSerializer,
    RegisterSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    ShipmentSerializer,
    ShipmentAssignDriverSerializer,
    ShipmentLocationUpdateSerializer,
    DeliveryAddressSerializer,
    MeSerializer,
    AdminUserSerializer,
    ChangePasswordSerializer,
    RoleChangeRequestSerializer,
)
from .permissions import IsStaffOrAdminRole


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        identifier = (
            request.data.get('username')
            or request.data.get('email')
            or request.data.get('identifier')
            or ''
        ).strip()
        password = request.data.get('password') or ''

        if not identifier or not password:
            return Response({'error': 'Debes enviar email/username y password.'}, status=400)

        user = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()

        if not user:
            return Response({'error': 'Usuario no existe'}, status=400)

        if not user.check_password(password):
            return Response({'error': 'Credenciales invalidas'}, status=400)

        refresh = RefreshToken.for_user(user)
        user_data = MeSerializer(user).data

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_data
        })


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminUserListView(generics.ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [IsStaffOrAdminRole]

    def get_queryset(self):
        return User.objects.all().select_related('profile').prefetch_related('groups')


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [IsStaffOrAdminRole]
    http_method_names = ['get', 'patch', 'put']

    def get_queryset(self):
        return User.objects.all().select_related('profile').prefetch_related('groups')


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_password = serializer.validated_data['current_password']
        new_password = serializer.validated_data['new_password']

        if not request.user.check_password(current_password):
            return Response({'error': 'La contrasena actual es incorrecta.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.check_password(new_password):
            return Response(
                {'error': 'La nueva contrasena debe ser diferente a la actual.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])

        return Response({'message': 'Contrasena actualizada correctamente.'}, status=status.HTTP_200_OK)


class ProductListView(generics.ListCreateAPIView):
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = (self.request.query_params.get('category_id') or '').strip()
        category_name = (self.request.query_params.get('category') or '').strip()

        if category_id.isdigit():
            if int(category_id) == 0:
                return queryset
            return queryset.filter(category_id=int(category_id))

        if category_name and category_name.lower() not in {'todos', 'all'}:
            return queryset.filter(category__name__iexact=category_name)

        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = [{
            'id': 0,
            'name': 'Todos',
            'order': 0,
            'image': '',
            'image_url': '',
        }] + list(response.data)
        return response


class BannerListView(generics.ListAPIView):
    serializer_class = BannerSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Banner.objects.filter(is_active=True).order_by('order', 'id')


class CartView(generics.ListCreateAPIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        quantity = serializer.validated_data.get('quantity', 1)

        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': quantity},
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save(update_fields=['quantity'])

        output_serializer = self.get_serializer(cart_item)
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        payload = dict(output_serializer.data)
        payload['message'] = (
            'Producto agregado al carrito'
            if created
            else 'Cantidad del producto actualizada en el carrito'
        )

        return Response(payload, status=response_status)

    def patch(self, request, *args, **kwargs):
        cart_item_id = (
            request.data.get('cart_item_id')
            or request.data.get('id')
            or request.query_params.get('cart_item_id')
            or request.query_params.get('id')
        )
        product_id = (
            request.data.get('product')
            or request.data.get('product_id')
            or request.query_params.get('product')
            or request.query_params.get('product_id')
        )
        quantity = request.data.get('quantity', request.data.get('cantidad'))

        if quantity is None:
            return Response({'error': 'Debes enviar quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({'error': 'quantity debe ser un numero entero.'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity < 0:
            return Response({'error': 'quantity no puede ser negativo.'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = Cart.objects.filter(user=request.user)
        if cart_item_id:
            queryset = queryset.filter(id=cart_item_id)
        elif product_id:
            queryset = queryset.filter(product_id=product_id)
        else:
            return Response(
                {'error': 'Debes enviar cart_item_id/id o product/product_id.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item = queryset.first()
        if not cart_item:
            return Response({'error': 'Producto no encontrado en el carrito.'}, status=status.HTTP_404_NOT_FOUND)

        if quantity == 0:
            cart_item.delete()
            return Response({'message': 'Producto eliminado del carrito.'}, status=status.HTTP_200_OK)

        cart_item.quantity = quantity
        cart_item.save(update_fields=['quantity'])
        output_serializer = self.get_serializer(cart_item)
        payload = dict(output_serializer.data)
        payload['message'] = 'Cantidad actualizada en el carrito'
        return Response(payload, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        cart_item_id = (
            request.data.get('cart_item_id')
            or request.data.get('id')
            or request.query_params.get('cart_item_id')
            or request.query_params.get('id')
        )
        product_id = (
            request.data.get('product')
            or request.data.get('product_id')
            or request.query_params.get('product')
            or request.query_params.get('product_id')
        )

        queryset = Cart.objects.filter(user=request.user)

        if cart_item_id:
            deleted_count, _ = queryset.filter(id=cart_item_id).delete()
            if deleted_count == 0:
                return Response({'error': 'Producto no encontrado en el carrito.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(
                {'message': 'Producto eliminado del carrito.', 'deleted': deleted_count},
                status=status.HTTP_200_OK
            )

        if product_id:
            deleted_count, _ = queryset.filter(product_id=product_id).delete()
            if deleted_count == 0:
                return Response({'error': 'Producto no encontrado en el carrito.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(
                {'message': 'Producto eliminado del carrito.', 'deleted': deleted_count},
                status=status.HTTP_200_OK
            )

        deleted_count, _ = queryset.delete()
        return Response(
            {'message': 'Carrito vaciado.', 'deleted': deleted_count},
            status=status.HTTP_200_OK
        )


class CartCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Cart.objects.filter(user=request.user)
        distinct_items = queryset.count()
        total_quantity = queryset.aggregate(total=Sum('quantity')).get('total') or 0

        return Response({
            'count': int(total_quantity),
            'distinct_items': distinct_items,
        })


def pick_auto_driver():
    group_driver_ids = set(
        User.objects.filter(
            is_active=True,
            groups__name__in=['DRIVER', 'REPARTIDOR'],
        ).values_list('id', flat=True)
    )
    requested_driver_ids = set(
        RoleChangeRequest.objects.filter(
            requested_role='driver',
            status='approved',
            user__is_active=True,
        ).values_list('user_id', flat=True)
    )
    candidate_ids = group_driver_ids.union(requested_driver_ids)
    if not candidate_ids:
        return None

    active_statuses = ['assigned', 'picked_up', 'on_the_way', 'nearby']
    return (
        User.objects.filter(id__in=candidate_ids, is_active=True)
        .annotate(
            active_shipments=Count(
                'shipments_assigned',
                filter=Q(shipments_assigned__status__in=active_statuses),
                distinct=True,
            ),
            first_active_shipment_at=Min(
                'shipments_assigned__created_at',
                filter=Q(shipments_assigned__status__in=active_statuses),
            ),
        )
        .order_by('active_shipments', 'first_active_shipment_at', 'id')
        .first()
    )


class OrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related('delivery_address')
            .prefetch_related('items__product')
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        user = request.user
        with transaction.atomic():
            cart_items = list(Cart.objects.select_related('product').filter(user=user))
            if not cart_items:
                return Response({'error': 'El carrito esta vacio.'}, status=status.HTTP_400_BAD_REQUEST)

            address = input_serializer.validated_data.get('delivery_address')
            if address and address.user_id != user.id:
                return Response(
                    {'error': 'La direccion seleccionada no pertenece al usuario autenticado.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if address is None:
                address = DeliveryAddress.objects.filter(user=user, is_default=True).first()
            if address is None:
                address = DeliveryAddress.objects.filter(user=user).order_by('-id').first()
            if address is None:
                return Response(
                    {'error': 'Debes registrar una direccion de entrega antes de crear un pedido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            product_ids = [item.product_id for item in cart_items]
            locked_products = Product.objects.select_for_update().filter(id__in=product_ids)
            products_by_id = {product.id: product for product in locked_products}

            stock_errors = []
            for cart_item in cart_items:
                product = products_by_id.get(cart_item.product_id)
                if not product:
                    stock_errors.append({
                        'product_id': cart_item.product_id,
                        'error': 'Producto no encontrado.',
                    })
                    continue
                if product.stock < cart_item.quantity:
                    stock_errors.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'requested': cart_item.quantity,
                        'available': product.stock,
                    })

            if stock_errors:
                return Response(
                    {
                        'error': 'No hay stock suficiente para completar el pedido.',
                        'details': stock_errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            order = Order.objects.create(
                user=user,
                delivery_address=address,
                delivery_main_address=address.main_address,
                delivery_secondary_street=address.secondary_street,
                delivery_apartment=address.apartment,
                delivery_city=address.city,
                delivery_instructions=address.delivery_instructions,
                status='pending',
                total_amount=Decimal('0.00'),
                total_items=0,
            )
            auto_driver = pick_auto_driver()
            shipment_status = 'assigned' if auto_driver else 'pending_assignment'
            Shipment.objects.create(
                order=order,
                driver=auto_driver,
                status=shipment_status,
            )
            if auto_driver:
                order.status = 'confirmed'
                order.save(update_fields=['status'])

            total_amount = Decimal('0.00')
            total_items = 0

            for cart_item in cart_items:
                product = products_by_id[cart_item.product_id]
                quantity = int(cart_item.quantity)
                subtotal = product.price * quantity

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_price=product.price,
                    quantity=quantity,
                    subtotal=subtotal,
                )

                product.stock -= quantity
                product.save(update_fields=['stock'])

                total_amount += subtotal
                total_items += quantity

            order.total_amount = total_amount
            order.total_items = total_items
            order.save(update_fields=['total_amount', 'total_items'])

            Cart.objects.filter(user=user).delete()

        output_serializer = OrderSerializer(order, context=self.get_serializer_context())
        payload = dict(output_serializer.data)
        payload['message'] = 'Pedido creado correctamente.'
        return Response(payload, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related('delivery_address')
            .prefetch_related('items__product')
        )


class OrderTrackingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        order_queryset = Order.objects.select_related(
            'delivery_address',
            'shipment',
            'shipment__driver',
        )
        if not request.user.is_staff:
            order_queryset = order_queryset.filter(user=request.user)

        order = order_queryset.filter(id=pk).first()
        if not order:
            return Response({'error': 'Pedido no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        shipment, _ = Shipment.objects.get_or_create(
            order=order,
            defaults={'status': 'pending_assignment'},
        )
        if shipment.driver_id is None:
            auto_driver = pick_auto_driver()
            if auto_driver:
                shipment.driver = auto_driver
                if shipment.status == 'pending_assignment':
                    shipment.status = 'assigned'
                shipment.save(update_fields=['driver', 'status', 'updated_at'])
                if order.status == 'pending':
                    order.status = 'confirmed'
                    order.save(update_fields=['status'])
        shipment_data = ShipmentSerializer(shipment, context={'request': request}).data

        return Response({
            'order': {
                'id': order.id,
                'status': order.status,
                'status_label': order.get_status_display(),
                'total_amount': order.total_amount,
                'total_items': order.total_items,
                'created_at': order.created_at,
                'delivery_city': order.delivery_city,
                'delivery_main_address': order.delivery_main_address,
            },
            'shipment': shipment_data,
        })


class OrderTrackingLocationUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _can_update_tracking(self, user, shipment):
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        allowed_groups = ['ADMIN', 'DRIVER', 'REPARTIDOR']
        is_ops_user = user.groups.filter(name__in=allowed_groups).exists()

        if shipment.driver_id and shipment.driver_id == user.id:
            return True

        if is_ops_user and shipment.driver_id is None:
            return True

        return False

    def post(self, request, pk):
        order_queryset = Order.objects.select_related('shipment', 'shipment__driver')
        if not request.user.is_staff:
            order_queryset = order_queryset.filter(
                Q(user=request.user) | Q(shipment__driver=request.user)
            )

        order = order_queryset.filter(id=pk).first()
        if not order:
            return Response({'error': 'Pedido no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        shipment, _ = Shipment.objects.get_or_create(
            order=order,
            defaults={'status': 'pending_assignment'},
        )

        if not self._can_update_tracking(request.user, shipment):
            return Response(
                {'error': 'No tienes permisos para actualizar la ubicacion de este envio.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ShipmentLocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        shipment.current_latitude = data['latitude']
        shipment.current_longitude = data['longitude']
        shipment.last_location_at = timezone.now()

        if 'heading' in data:
            shipment.current_heading = data.get('heading')
        if 'speed' in data:
            shipment.current_speed = data.get('speed')
        if 'status' in data:
            shipment.status = data['status']
        if 'eta_minutes' in data:
            shipment.eta_minutes = data.get('eta_minutes')
        if 'notes' in data:
            shipment.notes = data.get('notes', '')

        shipment.save()

        ShipmentLocation.objects.create(
            shipment=shipment,
            latitude=data['latitude'],
            longitude=data['longitude'],
            heading=data.get('heading'),
            speed=data.get('speed'),
        )

        order_status_map = {
            'pending_assignment': 'pending',
            'assigned': 'confirmed',
            'picked_up': 'preparing',
            'on_the_way': 'on_the_way',
            'nearby': 'on_the_way',
            'delivered': 'delivered',
            'cancelled': 'cancelled',
        }
        mapped_status = order_status_map.get(shipment.status)
        if mapped_status and mapped_status != order.status:
            order.status = mapped_status
            order.save(update_fields=['status'])

        payload = ShipmentSerializer(shipment, context={'request': request}).data
        payload['message'] = 'Ubicacion de envio actualizada.'
        return Response(payload, status=status.HTTP_200_OK)


class OrderTrackingAssignDriverView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _can_assign(self, user):
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return user.groups.filter(name='ADMIN').exists()

    def post(self, request, pk):
        if not self._can_assign(request.user):
            return Response(
                {'error': 'No tienes permisos para asignar repartidor.'},
                status=status.HTTP_403_FORBIDDEN
            )

        order = (
            Order.objects.select_related('shipment', 'shipment__driver')
            .filter(id=pk)
            .first()
        )
        if not order:
            return Response({'error': 'Pedido no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        shipment, _ = Shipment.objects.get_or_create(
            order=order,
            defaults={'status': 'pending_assignment'},
        )

        serializer = ShipmentAssignDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        has_driver_id = 'driver_id' in validated
        driver_id = validated.get('driver_id')
        auto_assign = validated.get('auto_assign')

        # Regla pedida:
        # - body vacio => auto asignar
        # - auto_assign=true => auto asignar
        # - driver_id=null => desasignar explicito
        if auto_assign is None and not has_driver_id:
            auto_assign = True

        if auto_assign:
            auto_driver = pick_auto_driver()
            if auto_driver is None:
                shipment.driver = None
                if shipment.status not in {'delivered', 'cancelled'}:
                    shipment.status = 'pending_assignment'
                shipment.save(update_fields=['driver', 'status', 'updated_at'])
                payload = ShipmentSerializer(shipment, context={'request': request}).data
                payload['message'] = 'No hay repartidores disponibles para auto-asignacion.'
                return Response(payload, status=status.HTTP_200_OK)

            shipment.driver = auto_driver
            if shipment.status in {'pending_assignment', 'cancelled'}:
                shipment.status = 'assigned'
            shipment.save(update_fields=['driver', 'status', 'updated_at'])

            if order.status == 'pending':
                order.status = 'confirmed'
                order.save(update_fields=['status'])

            payload = ShipmentSerializer(shipment, context={'request': request}).data
            payload['message'] = 'Repartidor auto-asignado correctamente.'
            return Response(payload, status=status.HTTP_200_OK)

        if has_driver_id and driver_id is None:
            shipment.driver = None
            if shipment.status not in {'delivered', 'cancelled'}:
                shipment.status = 'pending_assignment'
            shipment.save(update_fields=['driver', 'status', 'updated_at'])
            payload = ShipmentSerializer(shipment, context={'request': request}).data
            payload['message'] = 'Repartidor desasignado correctamente.'
            return Response(payload, status=status.HTTP_200_OK)

        if not has_driver_id:
            return Response(
                {'error': 'Debes enviar driver_id, driver_id=null o auto_assign=true.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        driver = User.objects.get(id=driver_id)
        shipment.driver = driver
        if shipment.status == 'pending_assignment':
            shipment.status = 'assigned'
        shipment.save(update_fields=['driver', 'status', 'updated_at'])

        if order.status == 'pending':
            order.status = 'confirmed'
            order.save(update_fields=['status'])

        payload = ShipmentSerializer(shipment, context={'request': request}).data
        payload['message'] = 'Repartidor asignado correctamente.'
        return Response(payload, status=status.HTTP_200_OK)


class DeliveryAddressListCreateView(generics.ListCreateAPIView):
    serializer_class = DeliveryAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DeliveryAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        queryset = DeliveryAddress.objects.filter(user=self.request.user)
        requested_default = serializer.validated_data.get('is_default', False)
        should_be_default = requested_default or not queryset.exists()

        address = serializer.save(user=self.request.user, is_default=should_be_default)
        if should_be_default:
            queryset.exclude(id=address.id).update(is_default=False)


class DeliveryAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DeliveryAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DeliveryAddress.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        address = serializer.save()
        if address.is_default:
            DeliveryAddress.objects.filter(user=self.request.user).exclude(id=address.id).update(is_default=False)
            return

        has_default = DeliveryAddress.objects.filter(user=self.request.user, is_default=True).exists()
        if not has_default:
            address.is_default = True
            address.save(update_fields=['is_default'])

    def perform_destroy(self, instance):
        user = instance.user
        was_default = instance.is_default
        instance.delete()

        if was_default:
            replacement = DeliveryAddress.objects.filter(user=user).order_by('-id').first()
            if replacement:
                replacement.is_default = True
                replacement.save(update_fields=['is_default'])


class RoleChangeRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = RoleChangeRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RoleChangeRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        requested_role = serializer.validated_data['requested_role']
        has_pending = RoleChangeRequest.objects.filter(
            user=self.request.user,
            requested_role=requested_role,
            status='pending',
        ).exists()
        if has_pending:
            raise serializers.ValidationError({
                'requested_role': 'Ya tienes una solicitud pendiente para este rol.'
            })
        serializer.save(user=self.request.user)


def geo_provider():
    return (getattr(settings, 'GEO_PROVIDER', 'osm') or 'osm').strip().lower()


def osm_nominatim_base_url():
    return (getattr(settings, 'OSM_NOMINATIM_BASE_URL', 'https://nominatim.openstreetmap.org') or '').rstrip('/')


def osm_router_base_url():
    return (getattr(settings, 'OSM_ROUTER_BASE_URL', 'https://router.project-osrm.org') or '').rstrip('/')


def geocoder_user_agent():
    return (getattr(settings, 'GEOCODER_USER_AGENT', 'api-technova/1.0 (mobile-app)') or 'api-technova/1.0')


def http_json_get(endpoint, params=None, timeout=8, headers=None):
    url = endpoint if not params else f"{endpoint}?{urlencode(params)}"
    req = Request(
        url,
        headers=headers or {
            'Accept': 'application/json',
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def extract_nominatim_result(item):
    address = item.get('address') or {}
    display_name = item.get('display_name') or ''
    road = (
        address.get('road')
        or address.get('pedestrian')
        or address.get('footway')
        or address.get('path')
        or address.get('cycleway')
        or ''
    )
    house_number = address.get('house_number') or ''
    main_address = (
        f"{road} {house_number}".strip()
        or road
        or (display_name.split(',')[0].strip() if display_name else '')
    )
    secondary_street = (
        address.get('suburb')
        or address.get('neighbourhood')
        or address.get('quarter')
        or address.get('city_district')
        or ''
    )
    city = (
        address.get('city')
        or address.get('town')
        or address.get('village')
        or address.get('hamlet')
        or ''
    )
    region = address.get('state') or address.get('county') or ''
    country_name = address.get('country') or ''

    try:
        lat = float(item.get('lat')) if item.get('lat') is not None else None
    except (TypeError, ValueError):
        lat = None
    try:
        lng = float(item.get('lon')) if item.get('lon') is not None else None
    except (TypeError, ValueError):
        lng = None

    return {
        'place_id': str(item.get('place_id') or ''),
        'osm_id': str(item.get('osm_id') or ''),
        'osm_type': item.get('osm_type') or '',
        'label': display_name,
        'main_address': main_address,
        'secondary_street': secondary_street,
        'city': city,
        'region': region,
        'country': country_name,
        'lat': lat,
        'lng': lng,
    }


def parse_google_duration(value):
    if not value or not isinstance(value, str):
        return None
    if not value.endswith('s'):
        return None
    try:
        return int(float(value[:-1]))
    except (TypeError, ValueError):
        return None


class GeoAutocompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _google_api_key(self):
        return (getattr(settings, 'GOOGLE_MAPS_SERVER_API_KEY', '') or '').strip()

    def _google_language(self):
        return (getattr(settings, 'GOOGLE_MAPS_LANGUAGE', 'es') or 'es').strip()

    def _google_region(self):
        return (getattr(settings, 'GOOGLE_MAPS_REGION', 'ec') or 'ec').strip().lower()

    def _http_json_get(self, endpoint, params, timeout=6):
        req = Request(
            f"{endpoint}?{urlencode(params)}",
            headers={
                'Accept': 'application/json',
            },
        )
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def _extract_from_geocode_result(self, geocode_result):
        components = geocode_result.get('address_components') or []
        values = {}
        for component in components:
            name = component.get('long_name') or ''
            for ctype in component.get('types') or []:
                if ctype not in values:
                    values[ctype] = name

        road = values.get('route') or ''
        house_number = values.get('street_number') or ''
        main_address = (
            f"{road} {house_number}".strip()
            or geocode_result.get('formatted_address', '').split(',')[0].strip()
        )
        secondary_street = (
            values.get('sublocality')
            or values.get('sublocality_level_1')
            or values.get('neighborhood')
            or values.get('premise')
            or ''
        )
        city = (
            values.get('locality')
            or values.get('administrative_area_level_2')
            or values.get('postal_town')
            or ''
        )
        region = values.get('administrative_area_level_1') or ''
        country_name = values.get('country') or ''

        geometry = geocode_result.get('geometry') or {}
        location = geometry.get('location') or {}
        try:
            lat = float(location.get('lat')) if location.get('lat') is not None else None
        except (TypeError, ValueError):
            lat = None
        try:
            lng = float(location.get('lng')) if location.get('lng') is not None else None
        except (TypeError, ValueError):
            lng = None

        return {
            'label': geocode_result.get('formatted_address', ''),
            'main_address': main_address,
            'secondary_street': secondary_street,
            'city': city,
            'region': region,
            'country': country_name,
            'lat': lat,
            'lng': lng,
        }

    def _geocode_place_id(self, place_id):
        key = self._google_api_key()
        if not key or not place_id:
            return None
        params = {
            'place_id': place_id,
            'language': self._google_language(),
            'key': key,
        }
        payload = self._http_json_get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params,
        )
        if payload.get('status') != 'OK':
            return None
        results = payload.get('results') or []
        if not results:
            return None
        return self._extract_from_geocode_result(results[0])

    def get(self, request):
        query = (request.query_params.get('q') or request.query_params.get('query') or '').strip()
        if len(query) < 3:
            return Response({'results': [], 'provider': geo_provider()})

        country = (request.query_params.get('country') or self._google_region()).strip().lower()
        try:
            limit = int(request.query_params.get('limit', 5))
        except (TypeError, ValueError):
            limit = 5
        limit = max(1, min(limit, 10))

        if geo_provider() != 'google':
            params = {
                'format': 'jsonv2',
                'addressdetails': 1,
                'countrycodes': country,
                'limit': limit,
                'q': query,
            }
            try:
                payload = http_json_get(
                    f'{osm_nominatim_base_url()}/search',
                    params,
                    headers={
                        'User-Agent': geocoder_user_agent(),
                        'Accept': 'application/json',
                    }
                ) or []
            except Exception:
                return Response({'results': [], 'provider': 'osm'})

            results = [extract_nominatim_result(item) for item in payload]
            return Response({'results': results, 'provider': 'osm'})

        key = self._google_api_key()
        if not key:
            return Response(
                {
                    'results': [],
                    'provider': 'google',
                    'error': 'Falta configurar GOOGLE_MAPS_SERVER_API_KEY en el backend.',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        params = {
            'input': query,
            'language': self._google_language(),
            'components': f'country:{country}',
            'types': 'address',
            'key': key,
        }
        try:
            payload = self._http_json_get(
                'https://maps.googleapis.com/maps/api/place/autocomplete/json',
                params,
            )
        except Exception:
            return Response({'results': [], 'provider': 'google'})

        status_name = payload.get('status')
        if status_name not in {'OK', 'ZERO_RESULTS'}:
            return Response({
                'results': [],
                'provider': 'google',
                'error': payload.get('error_message') or status_name or 'Autocomplete fallo.',
            })

        predictions = (payload.get('predictions') or [])[:limit]
        results = []
        for item in predictions:
            place_id = item.get('place_id') or ''
            geocoded = self._geocode_place_id(place_id) or {}
            label = item.get('description') or geocoded.get('label') or ''
            structured = item.get('structured_formatting') or {}
            main_text = structured.get('main_text') or ''
            secondary_text = structured.get('secondary_text') or ''

            results.append({
                'place_id': place_id,
                'label': label,
                'main_text': main_text,
                'secondary_text': secondary_text,
                'main_address': geocoded.get('main_address') or main_text or label,
                'secondary_street': geocoded.get('secondary_street') or secondary_text or '',
                'city': geocoded.get('city') or '',
                'region': geocoded.get('region') or '',
                'country': geocoded.get('country') or '',
                'lat': geocoded.get('lat'),
                'lng': geocoded.get('lng'),
            })

        return Response({'results': results, 'provider': 'google'})


class GeoGeocodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _google_api_key(self):
        return (getattr(settings, 'GOOGLE_MAPS_SERVER_API_KEY', '') or '').strip()

    def _google_language(self):
        return (getattr(settings, 'GOOGLE_MAPS_LANGUAGE', 'es') or 'es').strip()

    def _http_json_get(self, endpoint, params, timeout=6):
        req = Request(
            f"{endpoint}?{urlencode(params)}",
            headers={
                'Accept': 'application/json',
            },
        )
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def _extract_from_geocode_result(self, geocode_result):
        components = geocode_result.get('address_components') or []
        values = {}
        for component in components:
            name = component.get('long_name') or ''
            for ctype in component.get('types') or []:
                if ctype not in values:
                    values[ctype] = name

        road = values.get('route') or ''
        house_number = values.get('street_number') or ''
        main_address = (
            f"{road} {house_number}".strip()
            or geocode_result.get('formatted_address', '').split(',')[0].strip()
        )
        secondary_street = (
            values.get('sublocality')
            or values.get('sublocality_level_1')
            or values.get('neighborhood')
            or values.get('premise')
            or ''
        )
        city = (
            values.get('locality')
            or values.get('administrative_area_level_2')
            or values.get('postal_town')
            or ''
        )
        region = values.get('administrative_area_level_1') or ''
        country_name = values.get('country') or ''

        geometry = geocode_result.get('geometry') or {}
        location = geometry.get('location') or {}
        try:
            lat = float(location.get('lat')) if location.get('lat') is not None else None
        except (TypeError, ValueError):
            lat = None
        try:
            lng = float(location.get('lng')) if location.get('lng') is not None else None
        except (TypeError, ValueError):
            lng = None

        return {
            'place_id': geocode_result.get('place_id') or '',
            'label': geocode_result.get('formatted_address', ''),
            'main_address': main_address,
            'secondary_street': secondary_street,
            'city': city,
            'region': region,
            'country': country_name,
            'lat': lat,
            'lng': lng,
        }

    def get(self, request):
        place_id = (request.query_params.get('place_id') or '').strip()
        address = (request.query_params.get('q') or request.query_params.get('address') or '').strip()
        lat = (request.query_params.get('lat') or '').strip()
        lng = (request.query_params.get('lng') or '').strip()

        if geo_provider() != 'google':
            try:
                if lat and lng:
                    payload = http_json_get(
                        f'{osm_nominatim_base_url()}/reverse',
                        {
                            'format': 'jsonv2',
                            'addressdetails': 1,
                            'lat': lat,
                            'lon': lng,
                        },
                        headers={
                            'User-Agent': geocoder_user_agent(),
                            'Accept': 'application/json',
                        }
                    )
                    raw_results = [payload] if isinstance(payload, dict) else []
                elif address:
                    raw_results = http_json_get(
                        f'{osm_nominatim_base_url()}/search',
                        {
                            'format': 'jsonv2',
                            'addressdetails': 1,
                            'limit': 5,
                            'q': address,
                        },
                        headers={
                            'User-Agent': geocoder_user_agent(),
                            'Accept': 'application/json',
                        }
                    ) or []
                elif place_id:
                    raw_results = http_json_get(
                        f'{osm_nominatim_base_url()}/lookup',
                        {
                            'format': 'jsonv2',
                            'addressdetails': 1,
                            'place_ids': place_id,
                        },
                        headers={
                            'User-Agent': geocoder_user_agent(),
                            'Accept': 'application/json',
                        }
                    ) or []
                else:
                    return Response(
                        {'error': 'Debes enviar place_id, q/address o lat+lng.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception:
                return Response({'results': [], 'provider': 'osm'})

            results = [extract_nominatim_result(item) for item in raw_results]
            return Response({'results': results, 'provider': 'osm'})

        key = self._google_api_key()
        if not key:
            return Response(
                {
                    'results': [],
                    'provider': 'google',
                    'error': 'Falta configurar GOOGLE_MAPS_SERVER_API_KEY en el backend.',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        params = {
            'language': self._google_language(),
            'key': key,
        }

        if place_id:
            params['place_id'] = place_id
        elif address:
            params['address'] = address
        elif lat and lng:
            params['latlng'] = f'{lat},{lng}'
        else:
            return Response(
                {'error': 'Debes enviar place_id, q/address o lat+lng.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payload = self._http_json_get(
                'https://maps.googleapis.com/maps/api/geocode/json',
                params,
            )
        except Exception:
            return Response({'results': [], 'provider': 'google'})

        status_name = payload.get('status')
        if status_name not in {'OK', 'ZERO_RESULTS'}:
            return Response({
                'results': [],
                'provider': 'google',
                'error': payload.get('error_message') or status_name or 'Geocoding fallo.',
            })

        results = [
            self._extract_from_geocode_result(item)
            for item in (payload.get('results') or [])
        ]
        return Response({'results': results, 'provider': 'google'})


class GeoAddressValidationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _google_api_key(self):
        return (getattr(settings, 'GOOGLE_MAPS_SERVER_API_KEY', '') or '').strip()

    def _google_region(self):
        return (getattr(settings, 'GOOGLE_MAPS_REGION', 'EC') or 'EC').strip().upper()

    def _http_json_post(self, endpoint, payload, timeout=8):
        req = Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def post(self, request):
        address = (request.data.get('address') or '').strip()
        if not address:
            address = (
                request.data.get('main_address')
                or request.data.get('full_address')
                or request.data.get('q')
                or ''
            ).strip()

        if not address:
            return Response(
                {'error': 'Debes enviar address/main_address/full_address.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        secondary = (request.data.get('secondary_street') or '').strip()
        city = (request.data.get('city') or '').strip()
        region = (request.data.get('region') or '').strip()
        country = (request.data.get('country') or self._google_region()).strip()

        if geo_provider() != 'google':
            query = ', '.join([part for part in [address, secondary, city, region, country] if part]).strip()
            try:
                payload = http_json_get(
                    f'{osm_nominatim_base_url()}/search',
                    {
                        'format': 'jsonv2',
                        'addressdetails': 1,
                        'limit': 1,
                        'q': query,
                    },
                    headers={
                        'User-Agent': geocoder_user_agent(),
                        'Accept': 'application/json',
                    }
                ) or []
            except Exception:
                return Response({'provider': 'osm', 'valid': False, 'error': 'Address Validation fallo.'})

            first = payload[0] if payload else None
            if not first:
                return Response({
                    'provider': 'osm',
                    'valid': False,
                    'address_complete': False,
                    'formatted_address': '',
                    'place_id': '',
                    'lat': None,
                    'lng': None,
                    'raw': payload,
                })

            parsed = extract_nominatim_result(first)
            importance = first.get('importance')
            try:
                importance = float(importance) if importance is not None else None
            except (TypeError, ValueError):
                importance = None

            return Response({
                'provider': 'osm',
                'valid': True,
                'address_complete': True,
                'has_inferred_components': False,
                'has_unconfirmed_components': False,
                'formatted_address': parsed.get('label') or '',
                'place_id': parsed.get('place_id') or '',
                'lat': parsed.get('lat'),
                'lng': parsed.get('lng'),
                'confidence': importance,
                'raw': payload,
            })

        key = self._google_api_key()
        if not key:
            return Response(
                {
                    'provider': 'google',
                    'error': 'Falta configurar GOOGLE_MAPS_SERVER_API_KEY en el backend.',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        lines = [address]
        if secondary:
            lines.append(secondary)
        if city:
            lines.append(city)
        if region:
            lines.append(region)
        if country:
            lines.append(country)

        payload = {
            'address': {
                'addressLines': lines,
                'regionCode': self._google_region(),
            }
        }
        if country:
            payload['address']['regionCode'] = country[:2].upper()

        try:
            data = self._http_json_post(
                f'https://addressvalidation.googleapis.com/v1:validateAddress?key={key}',
                payload,
            )
        except Exception:
            return Response({'provider': 'google', 'valid': False, 'error': 'Address Validation fallo.'})

        verdict = data.get('result', {}).get('verdict', {})
        geocode = data.get('result', {}).get('geocode', {})
        location = geocode.get('location') or {}
        address_info = data.get('result', {}).get('address', {})

        try:
            lat = float(location.get('latitude')) if location.get('latitude') is not None else None
        except (TypeError, ValueError):
            lat = None
        try:
            lng = float(location.get('longitude')) if location.get('longitude') is not None else None
        except (TypeError, ValueError):
            lng = None

        is_valid = bool(verdict.get('addressComplete')) or bool(verdict.get('validationGranularity'))

        return Response({
            'provider': 'google',
            'valid': is_valid,
            'address_complete': bool(verdict.get('addressComplete')),
            'has_inferred_components': bool(verdict.get('hasInferredComponents')),
            'has_unconfirmed_components': bool(verdict.get('hasUnconfirmedComponents')),
            'formatted_address': address_info.get('formattedAddress') or '',
            'place_id': geocode.get('placeId') or '',
            'lat': lat,
            'lng': lng,
            'raw': data,
        })


class GeoRouteEstimateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _google_api_key(self):
        return (getattr(settings, 'GOOGLE_MAPS_SERVER_API_KEY', '') or '').strip()

    def _http_json_post(self, endpoint, payload, field_mask, timeout=8):
        req = Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Goog-FieldMask': field_mask,
            },
            method='POST',
        )
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def post(self, request):
        origin = request.data.get('origin') or {}
        destination = request.data.get('destination') or {}
        mode = (request.data.get('travel_mode') or 'DRIVE').strip().upper()

        if not isinstance(origin, dict) or not isinstance(destination, dict):
            return Response(
                {'error': 'origin y destination deben ser objetos con lat/lng.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if origin.get('lat') is None or origin.get('lng') is None:
            return Response({'error': 'origin.lat y origin.lng son obligatorios.'}, status=status.HTTP_400_BAD_REQUEST)
        if destination.get('lat') is None or destination.get('lng') is None:
            return Response(
                {'error': 'destination.lat y destination.lng son obligatorios.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if geo_provider() != 'google':
            profile_map = {
                'DRIVE': 'driving',
                'WALK': 'walking',
                'BICYCLE': 'cycling',
                'TWO_WHEELER': 'driving',
            }
            profile = profile_map.get(mode, 'driving')
            try:
                orig_lat = float(origin['lat'])
                orig_lng = float(origin['lng'])
                dst_lat = float(destination['lat'])
                dst_lng = float(destination['lng'])
            except (TypeError, ValueError):
                return Response({'error': 'lat/lng deben ser numericos.'}, status=status.HTTP_400_BAD_REQUEST)

            endpoint = (
                f"{osm_router_base_url()}/route/v1/{profile}/"
                f"{orig_lng},{orig_lat};{dst_lng},{dst_lat}"
            )
            try:
                data = http_json_get(
                    endpoint,
                    {
                        'overview': 'full',
                        'geometries': 'polyline',
                        'alternatives': str(bool(request.data.get('alternatives', False))).lower(),
                        'steps': 'false',
                    },
                    headers={'Accept': 'application/json'}
                )
            except Exception:
                return Response({'provider': 'osm', 'routes': [], 'error': 'Routes API fallo.'})

            if (data or {}).get('code') != 'Ok':
                return Response({
                    'provider': 'osm',
                    'routes': [],
                    'error': (data or {}).get('message') or 'No se pudo calcular la ruta.',
                    'raw': data,
                })

            routes = data.get('routes') or []
            normalized = []
            for route in routes:
                distance_m = route.get('distance')
                duration_sec = route.get('duration')
                normalized.append({
                    'distance_meters': distance_m,
                    'distance_km': round(float(distance_m) / 1000, 2) if distance_m is not None else None,
                    'duration': f'{duration_sec}s' if duration_sec is not None else None,
                    'static_duration': f'{duration_sec}s' if duration_sec is not None else None,
                    'duration_seconds': int(duration_sec) if duration_sec is not None else None,
                    'static_duration_seconds': int(duration_sec) if duration_sec is not None else None,
                    'polyline': route.get('geometry') or '',
                    'leg': {
                        'distance_meters': distance_m,
                        'duration': f'{duration_sec}s' if duration_sec is not None else None,
                        'static_duration': f'{duration_sec}s' if duration_sec is not None else None,
                        'polyline': route.get('geometry') or '',
                    },
                })

            return Response({'provider': 'osm', 'routes': normalized, 'raw': data})

        key = self._google_api_key()
        if not key:
            return Response(
                {
                    'provider': 'google',
                    'error': 'Falta configurar GOOGLE_MAPS_SERVER_API_KEY en el backend.',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        routing_preference = (request.data.get('routing_preference') or 'TRAFFIC_AWARE').strip().upper()
        units = (request.data.get('units') or 'METRIC').strip().upper()

        payload = {
            'origin': {
                'location': {
                    'latLng': {
                        'latitude': float(origin['lat']),
                        'longitude': float(origin['lng']),
                    }
                }
            },
            'destination': {
                'location': {
                    'latLng': {
                        'latitude': float(destination['lat']),
                        'longitude': float(destination['lng']),
                    }
                }
            },
            'travelMode': mode,
            'routingPreference': routing_preference,
            'computeAlternativeRoutes': bool(request.data.get('alternatives', False)),
            'units': units,
        }

        field_mask = ','.join([
            'routes.distanceMeters',
            'routes.duration',
            'routes.staticDuration',
            'routes.polyline.encodedPolyline',
            'routes.legs.distanceMeters',
            'routes.legs.duration',
            'routes.legs.staticDuration',
            'routes.legs.polyline.encodedPolyline',
        ])

        try:
            data = self._http_json_post(
                f'https://routes.googleapis.com/directions/v2:computeRoutes?key={key}',
                payload,
                field_mask=field_mask,
            )
        except Exception:
            return Response({'provider': 'google', 'routes': [], 'error': 'Routes API fallo.'})

        routes = data.get('routes') or []
        normalized = []
        for route in routes:
            distance_m = route.get('distanceMeters')
            duration_raw = route.get('duration')
            static_duration_raw = route.get('staticDuration')
            encoded_polyline = (route.get('polyline') or {}).get('encodedPolyline') or ''
            leg = (route.get('legs') or [{}])[0]
            normalized.append({
                'distance_meters': distance_m,
                'distance_km': round(float(distance_m) / 1000, 2) if distance_m is not None else None,
                'duration': duration_raw,
                'static_duration': static_duration_raw,
                'duration_seconds': self._parse_google_duration(duration_raw),
                'static_duration_seconds': self._parse_google_duration(static_duration_raw),
                'polyline': encoded_polyline,
                'leg': {
                    'distance_meters': leg.get('distanceMeters'),
                    'duration': leg.get('duration'),
                    'static_duration': leg.get('staticDuration'),
                    'polyline': (leg.get('polyline') or {}).get('encodedPolyline') or '',
                },
            })

        return Response({'provider': 'google', 'routes': normalized, 'raw': data})

    def _parse_google_duration(self, value):
        # Google duration viene como string tipo "123s".
        if not value or not isinstance(value, str):
            return None
        if not value.endswith('s'):
            return None
        try:
            return int(float(value[:-1]))
        except (TypeError, ValueError):
            return None
