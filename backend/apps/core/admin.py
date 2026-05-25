from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'country', 'reporting_year', 'created_at']
    search_fields = ['name', 'slug']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'organization', 'role', 'is_staff']
    list_filter = ['role', 'organization']
    fieldsets = UserAdmin.fieldsets + (
        ('ESG Profile', {'fields': ('organization', 'role')}),
    )
