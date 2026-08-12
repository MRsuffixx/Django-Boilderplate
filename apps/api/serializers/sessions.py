from rest_framework import serializers

from apps.authentication.models import UserSession
from apps.authentication.services import SessionService


class UserSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()
    is_revoked = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSession
        fields = [
            "id",
            "identifier",
            "ip_address",
            "browser",
            "operating_system",
            "device",
            "location",
            "created_at",
            "last_activity_at",
            "is_current",
            "is_revoked",
            "revoked_at",
        ]
        read_only_fields = fields

    def get_is_current(self, obj) -> bool:
        current = SessionService.current(self.context["request"])
        return bool(current and current.pk == obj.pk)
