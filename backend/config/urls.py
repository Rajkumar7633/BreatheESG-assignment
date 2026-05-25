from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path('', health_check, name='health_check'),
    path('admin/', admin.site.urls),

    # /auth/token/ — top-level (matches what the frontend calls)
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # /api/auth/token/ — with /api/ prefix (also supported)
    path('api/auth/token/', TokenObtainPairView.as_view(), name='api_token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),

    path('api/core/', include('apps.core.urls')),
    path('api/ingestion/', include('apps.ingestion.urls')),
    path('api/emissions/', include('apps.emissions.urls')),
    path('api/review/', include('apps.review.urls')),
]
