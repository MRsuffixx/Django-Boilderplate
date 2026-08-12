from django.contrib import admin

from apps.core.models import FeatureFlag, IdempotencyRecord, Setting


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ["key", "value_type", "group", "is_public", "updated_at"]
    list_filter = ["value_type", "group", "is_public"]
    search_fields = ["key", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ["key", "enabled", "updated_at"]
    list_filter = ["enabled"]
    search_fields = ["key", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "request_method", "request_path", "response_status", "created_at", "expires_at"]
    list_filter = ["request_method", "response_status", "created_at", "expires_at"]
    search_fields = ["user__email", "request_path"]
    readonly_fields = [field.name for field in IdempotencyRecord._meta.fields]
    exclude = ["key_hash", "request_hash", "response_body"]

    def has_add_permission(self, request):
        return False
