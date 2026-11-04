from django.contrib import admin
from .models import Organization, User

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')
    readonly_fields = ('id', 'slug', 'created_at')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'role', 'organization', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'organization')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

