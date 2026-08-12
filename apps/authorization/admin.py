from django.contrib import admin

from apps.authorization.models import (
    Permission,
    Role,
    RolePermission,
    UserPermissionOverride,
    UserRole,
)


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    autocomplete_fields = ["permission"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "priority", "is_system", "created_at"]
    list_filter = ["is_system", "priority"]
    search_fields = ["name", "slug", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [RolePermissionInline]

    def has_delete_permission(self, request, obj=None):
        return bool(
            super().has_delete_permission(request, obj) and (obj is None or not obj.is_system)
        )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["codename", "description", "is_system", "created_at"]
    list_filter = ["is_system"]
    search_fields = ["codename", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "valid_from", "valid_until", "granted_by"]
    list_filter = ["role", "valid_from", "valid_until"]
    search_fields = ["user__email", "user__username", "role__name"]
    autocomplete_fields = ["user", "role", "granted_by"]
    readonly_fields = ["id", "created_at"]


@admin.register(UserPermissionOverride)
class UserPermissionOverrideAdmin(admin.ModelAdmin):
    list_display = ["user", "permission", "effect", "granted_by", "updated_at"]
    list_filter = ["effect", "permission"]
    search_fields = ["user__email", "permission__codename", "reason"]
    autocomplete_fields = ["user", "permission", "granted_by"]
    readonly_fields = ["id", "created_at", "updated_at"]
