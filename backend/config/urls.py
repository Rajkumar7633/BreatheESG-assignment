from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/core/', include('apps.core.urls')),
    path('api/ingestion/', include('apps.ingestion.urls')),
    path('api/emissions/', include('apps.emissions.urls')),
    path('api/review/', include('apps.review.urls')),
]
