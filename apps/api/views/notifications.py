from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action

from apps.api.serializers.notifications import NotificationSerializer
from apps.api_keys.permissions import HasAPIKeyScope
from apps.notifications.models import Notification
from common.responses import success_response


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [HasAPIKeyScope]
    required_api_key_scopes = ("notifications.read",)
    filterset_fields = ["type"]
    ordering_fields = ["created_at", "expires_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.read_at:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return success_response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        count = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return success_response({"updated_count": count})

    def destroy(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.delete()
        return success_response({"deleted": True})
