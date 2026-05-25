from django.urls import path
from . import views

urlpatterns = [
    path('queue/', views.review_queue, name='review-queue'),
    path('records/<uuid:record_id>/action/', views.single_action, name='review-single-action'),
    path('bulk/', views.bulk_action, name='review-bulk'),
    path('audit-log/', views.audit_log, name='review-audit-log'),
]
