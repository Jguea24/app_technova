from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group, User
from django.utils.html import format_html
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

# Register your models here.

ROLE_CHOICES = (
    ('cliente', 'Cliente'),
    ('admin', 'Admin'),
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'image_preview')
    ordering = ('order', 'name')
    search_fields = ('name',)
    readonly_fields = ('image_preview',)

    @admin.display(description='Imagen')
    def image_preview(self, obj):
        if not obj.image:
            return '-'
        return format_html(
            '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:6px;" />',
            obj.image.url
        )


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'image_preview')
    list_filter = ('is_active',)
    ordering = ('order', 'id')
    search_fields = ('title',)
    readonly_fields = ('image_preview',)

    @admin.display(description='Imagen')
    def image_preview(self, obj):
        if not obj.image:
            return '-'
        return format_html(
            '<img src="{}" style="height:56px;width:120px;object-fit:cover;border-radius:8px;" />',
            obj.image.url
        )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'short_description',
        'price',
        'old_price',
        'rating',
        'reviews_count',
        'stock',
        'image_preview',
    )
    search_fields = ('name', 'description', 'category__name')
    list_filter = ('category', 'price',)
    readonly_fields = ('image_preview',)

    @admin.display(description='Imagen')
    def image_preview(self, obj):
        if not obj.image:
            return '-'
        return format_html(
            '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:6px;" />',
            obj.image.url
        )

    @admin.display(description='Descripcion')
    def short_description(self, obj):
        text = (obj.description or '').strip()
        if len(text) <= 40:
            return text
        return f'{text[:40]}...'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity')
    search_fields = ('user__username', 'product__name')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'address')
    search_fields = ('user__username', 'user__email', 'phone', 'address')


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'main_address', 'city', 'is_default', 'created_at')
    list_filter = ('city', 'is_default')
    search_fields = ('user__username', 'user__email', 'main_address', 'secondary_street', 'apartment', 'city')


@admin.register(RoleChangeRequest)
class RoleChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'requested_role', 'status', 'created_at')
    list_filter = ('requested_role', 'status')
    search_fields = ('user__username', 'user__email', 'reason')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ('product', 'product_name', 'product_price', 'quantity', 'subtotal')
    readonly_fields = ('product', 'product_name', 'product_price', 'quantity', 'subtotal')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_items', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = (
        'id',
        'user__username',
        'user__email',
        'delivery_main_address',
        'delivery_city',
    )
    readonly_fields = ('created_at', 'updated_at')
    inlines = (OrderItemInline,)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'quantity', 'product_price', 'subtotal')
    list_filter = ('order__status',)
    search_fields = ('order__id', 'product_name', 'order__user__username')


class ShipmentLocationInline(admin.TabularInline):
    model = ShipmentLocation
    extra = 0
    can_delete = False
    readonly_fields = ('latitude', 'longitude', 'heading', 'speed', 'recorded_at')
    fields = ('latitude', 'longitude', 'heading', 'speed', 'recorded_at')


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'driver',
        'status',
        'current_latitude',
        'current_longitude',
        'last_location_at',
        'updated_at',
    )
    list_filter = ('status', 'updated_at')
    search_fields = ('order__id', 'order__user__username', 'driver__username')
    readonly_fields = ('created_at', 'updated_at', 'last_location_at')
    inlines = (ShipmentLocationInline,)


@admin.register(ShipmentLocation)
class ShipmentLocationAdmin(admin.ModelAdmin):
    list_display = ('shipment', 'latitude', 'longitude', 'heading', 'speed', 'recorded_at')
    list_filter = ('recorded_at',)
    search_fields = ('shipment__order__id', 'shipment__order__user__username')


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fk_name = 'user'


class RoleUserChangeForm(UserChangeForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=False, label='Rol')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            roles = set(self.instance.groups.values_list('name', flat=True))
            if self.instance.is_superuser or 'ADMIN' in roles:
                self.fields['role'].initial = 'admin'
            else:
                self.fields['role'].initial = 'cliente'


class RoleUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=False, label='Rol')


class UserAdmin(BaseUserAdmin):

    inlines = (UserProfileInline,)
    list_display = BaseUserAdmin.list_display + ('role', 'phone', 'address')
    form = RoleUserChangeForm
    add_form = RoleUserCreationForm
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Rol', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Rol', {'fields': ('role',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile').prefetch_related('groups')

    def _apply_role(self, obj, role):
        role = (role or '').strip().lower()
        if obj.is_superuser:
            role = 'admin'
        role_groups = Group.objects.filter(
            name__in={'ADMIN', 'CLIENTE', 'DRIVER', 'PROVIDER', 'REPARTIDOR'}
        )
        if role_groups.exists():
            obj.groups.remove(*role_groups)

        if role == 'admin':
            admin_group, _ = Group.objects.get_or_create(name='ADMIN')
            obj.groups.add(admin_group)
            obj.is_staff = True
        elif role == 'cliente':
            cliente_group, _ = Group.objects.get_or_create(name='CLIENTE')
            obj.groups.add(cliente_group)
            if not obj.is_superuser:
                obj.is_staff = False
        elif not obj.is_superuser:
            obj.is_staff = False

    @admin.display(description='Rol')
    def role(self, obj):
        role_set = set(obj.groups.values_list('name', flat=True))
        if obj.is_superuser or 'ADMIN' in role_set:
            return 'ADMIN'
        if 'DRIVER' in role_set or 'REPARTIDOR' in role_set:
            return 'DRIVER'
        if 'PROVIDER' in role_set:
            return 'PROVIDER'
        if 'CLIENTE' in role_set:
            return 'CLIENTE'
        return '-'

    @admin.display(description='Phone')
    def phone(self, obj):
        return getattr(getattr(obj, 'profile', None), 'phone', '')

    @admin.display(description='Address')
    def address(self, obj):
        return getattr(getattr(obj, 'profile', None), 'address', '')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        role = None
        if hasattr(form, 'cleaned_data'):
            role = form.cleaned_data.get('role')
        self._apply_role(form.instance, role)
        form.instance.save(update_fields=['is_staff'])


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
