from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import Banner, Category, Product, Cart, UserProfile, DeliveryAddress, RoleChangeRequest

# Register your models here.

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


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = BaseUserAdmin.list_display + ('phone', 'address')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')

    @admin.display(description='Phone')
    def phone(self, obj):
        return getattr(getattr(obj, 'profile', None), 'phone', '')

    @admin.display(description='Address')
    def address(self, obj):
        return getattr(getattr(obj, 'profile', None), 'address', '')


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
