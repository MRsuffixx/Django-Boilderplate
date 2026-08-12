from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "actor", "target_type", "target_repr", "request_id", "created_at"]
    list_filter = ["action", "target_type", "created_at"]
    search_fields = ["action", "target_id", "target_repr", "request_id", "actor__email"]
    readonly_fields = [field.name for field in AuditLog._meta.fields]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
