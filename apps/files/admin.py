from django.contrib import admin

from apps.files.models import StoredFile


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = [
        "original_name",
        "owner",
        "content_type",
        "size",
        "status",
        "created_at",
        "deleted_at",
    ]
    list_filter = ["status", "content_type", "created_at", "deleted_at"]
    search_fields = ["original_name", "owner__email", "checksum_sha256"]
    autocomplete_fields = ["owner"]
    readonly_fields = [
        "id",
        "checksum_sha256",
        "size",
        "content_type",
        "created_at",
        "last_accessed_at",
        "deleted_at",
    ]
