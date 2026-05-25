from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('organizations', views.OrganizationViewSet, basename='organization')

urlpatterns = [
    path('me/', views.me, name='me'),
    path('', include(router.urls)),
]
