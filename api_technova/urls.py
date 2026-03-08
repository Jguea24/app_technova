from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from app.views import (
    AdminUserDetailView,
    AdminUserListView,
    BannerListView,
    CartCountView,
    CartView,
    CategoryListView,
    ChangePasswordView,
    DeliveryAddressDetailView,
    DeliveryAddressListCreateView,
    GeoAddressValidationView,
    GeoAutocompleteView,
    GeoGeocodeView,
    GeoRouteEstimateView,
    LoginView,
    MeView,
    OrderDetailView,
    OrderListCreateView,
    OrderTrackingAssignDriverView,
    OrderTrackingLocationUpdateView,
    OrderTrackingView,
    ProductDetailView,
    ProductListView,
    RegisterView,
    RoleChangeRequestListCreateView,
)


def home(request):
    return JsonResponse(
        {
            "status": "OK",
            "message": "API TechNova funcionando correctamente. Endpoints disponibles: admin/, register/, login/, token/refresh/, products/, cart/.",
        }
    )


urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("me/", MeView.as_view()),
    path("me/change-password/", ChangePasswordView.as_view()),
    path("users/", AdminUserListView.as_view()),
    path("users/<int:pk>/", AdminUserDetailView.as_view()),
    path("banners/", BannerListView.as_view()),
    path("categories/", CategoryListView.as_view()),
    path("products/", ProductListView.as_view()),
    path("products/<int:pk>/", ProductDetailView.as_view()),
    path("cart/count/", CartCountView.as_view()),
    path("cart/", CartView.as_view()),
    path("orders/", OrderListCreateView.as_view()),
    path("orders/<int:pk>/", OrderDetailView.as_view()),
    path("orders/<int:pk>/tracking/", OrderTrackingView.as_view()),
    path("orders/<int:pk>/tracking/assign-driver/", OrderTrackingAssignDriverView.as_view()),
    path("orders/<int:pk>/tracking/location/", OrderTrackingLocationUpdateView.as_view()),
    path("addresses/", DeliveryAddressListCreateView.as_view()),
    path("addresses/<int:pk>/", DeliveryAddressDetailView.as_view()),
    path("role-requests/", RoleChangeRequestListCreateView.as_view()),
    path("geo/autocomplete/", GeoAutocompleteView.as_view()),
    path("geo/geocode/", GeoGeocodeView.as_view()),
    path("geo/validate-address/", GeoAddressValidationView.as_view()),
    path("geo/routes/estimate/", GeoRouteEstimateView.as_view()),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
