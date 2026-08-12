from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action

from apps.api.serializers.api_keys import APIKeySerializer
from apps.api.throttles import APIKeyThrottle
from apps.api_keys.models import APIKey
from apps.api_keys.services import APIKeyService
from common.exceptions import APIException
from common.idempotency import idempotent
from common.responses import success_response


class APIKeyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = APIKeySerializer
    throttle_classes = [APIKeyThrottle]
    ordering_fields = ["created_at", "last_used_at", "expires_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return APIKey.objects.filter(owner=self.request.user)

    @idempotent()
    def create(self, request, *args, **kwargs):
        if not settings.ENABLE_API_KEYS:
            raise APIException("API keys are disabled.", code="FEATURE_DISABLED", status_code=404)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        api_key, raw = APIKeyService.create(
            owner=request.user, actor=request.user, request=request, **serializer.validated_data
        )
        data = self.get_serializer(api_key).data
        data["key"] = raw
        return success_response(data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        api_key = self.get_object()
        APIKeyService.revoke(api_key=api_key, actor=request.user, request=request)
        return success_response({"revoked": True})
