import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework import generics, permissions, serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.exceptions import ObjectDoesNotExist

from .models import Banner, Category, Product, Cart, DeliveryAddress, RoleChangeRequest
from .serializers import (
    BannerSerializer,
    CategorySerializer,
    ProductSerializer,
    CartSerializer,
    RegisterSerializer,
    DeliveryAddressSerializer,
    MeSerializer,
    ChangePasswordSerializer,
    RoleChangeRequestSerializer,
)


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


class GeoAutocompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = (request.query_params.get('q') or request.query_params.get('query') or '').strip()
        if len(query) < 3:
            return Response({'results': []})

        country = (request.query_params.get('country') or 'ec').strip().lower()
        try:
            limit = int(request.query_params.get('limit', 5))
        except (TypeError, ValueError):
            limit = 5
        limit = max(1, min(limit, 10))

        params = {
            'format': 'jsonv2',
            'addressdetails': 1,
            'countrycodes': country,
            'limit': limit,
            'q': query,
        }
        endpoint = f"https://nominatim.openstreetmap.org/search?{urlencode(params)}"
        user_agent = getattr(settings, 'GEOCODER_USER_AGENT', 'api-guayabal/1.0 (mobile-app)')

        try:
            req = Request(
                endpoint,
                headers={
                    'User-Agent': user_agent,
                    'Accept': 'application/json',
                },
            )
            with urlopen(req, timeout=6) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
        except Exception:
            return Response({'results': []})

        results = []
        for item in payload:
            display_name = item.get('display_name', '')
            address = item.get('address') or {}
            city = (
                address.get('city')
                or address.get('town')
                or address.get('village')
                or address.get('hamlet')
                or ''
            )
            region = address.get('state') or address.get('county') or ''
            country_name = address.get('country') or ''
            road = (
                address.get('road')
                or address.get('pedestrian')
                or address.get('footway')
                or address.get('path')
                or address.get('cycleway')
                or ''
            )
            house_number = address.get('house_number') or ''
            place_name = address.get('name') or ''
            main_address = (
                f"{road} {house_number}".strip()
                or road
                or place_name
                or (display_name.split(',')[0].strip() if display_name else '')
            )
            secondary_street = (
                address.get('suburb')
                or address.get('neighbourhood')
                or address.get('quarter')
                or address.get('city_district')
                or ''
            )

            try:
                lat = float(item.get('lat')) if item.get('lat') is not None else None
            except (TypeError, ValueError):
                lat = None

            try:
                lng = float(item.get('lon')) if item.get('lon') is not None else None
            except (TypeError, ValueError):
                lng = None

            results.append({
                'label': display_name,
                'main_address': main_address,
                'secondary_street': secondary_street,
                'city': city,
                'region': region,
                'country': country_name,
                'lat': lat,
                'lng': lng,
            })

        return Response({'results': results})
