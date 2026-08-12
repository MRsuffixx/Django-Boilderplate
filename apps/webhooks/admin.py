from django.contrib import admin

from apps.webhooks.models import WebhookDelivery, WebhookEndpoint, WebhookEvent


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "url", "is_active", "updated_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "url", "owner__email"]
    autocomplete_fields = ["owner"]
    readonly_fields = ["id", "created_at", "updated_at"]
    exclude = ["secret_hash", "encrypted_secret"]


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "created_at"]
    list_filter = ["event_type", "created_at"]
    readonly_fields = [field.name for field in WebhookEvent._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ["endpoint", "event", "status", "attempt_count", "response_code", "last_attempt_at", "next_retry_at"]
    list_filter = ["status", "response_code", "last_attempt_at", "next_retry_at"]
    search_fields = ["endpoint__name", "event__event_type"]
    readonly_fields = [field.name for field in WebhookDelivery._meta.fields]

    def has_add_permission(self, request):
        return False
