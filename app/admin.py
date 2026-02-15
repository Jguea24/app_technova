from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Product, Cart, UserProfile

# Register your models here.

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock')
    search_fields = ('name',)
    list_filter = ('price',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity')
    search_fields = ('user__username', 'product__name')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'address')
    search_fields = ('user__username', 'user__email', 'phone', 'address')


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
