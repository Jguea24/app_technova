from rest_framework.permissions import BasePermission

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name="ADMIN").exists()
        )

class IsClienteRole(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name="CLIENTE").exists()
        )


class IsStaffOrAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return (
            user.is_staff
            or user.is_superuser
            or user.groups.filter(name="ADMIN").exists()
        )
