from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmissionRecordViewSet, EmissionFactorViewSet

router = DefaultRouter()
router.register('records', EmissionRecordViewSet, basename='emission-record')
router.register('factors', EmissionFactorViewSet, basename='emission-factor')

urlpatterns = [
    path('', include(router.urls)),
]
