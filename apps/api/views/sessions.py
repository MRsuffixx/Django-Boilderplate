from rest_framework import viewsets
from rest_framework.decorators import action

from apps.api.serializers.sessions import UserSessionSerializer
from apps.authentication.models import UserSession
from apps.authentication.services import SessionService
from common.responses import success_response


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserSession.objects.none()
    serializer_class = UserSessionSerializer
    lookup_field = "identifier"
    ordering_fields = ["created_at", "last_activity_at"]
    ordering = ["-last_activity_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return self.request.user.user_sessions.all()

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, identifier=None):
        user_session = self.get_object()
        SessionService.revoke(user_session, actor=request.user, request=request)
        return success_response({"revoked": True})

    @action(detail=False, methods=["post"], url_path="revoke-others")
    def revoke_others(self, request):
        count = SessionService.revoke_all(
            user=request.user, actor=request.user, request=request, exclude_current=True
        )
        return success_response({"revoked_count": count})

    @action(detail=False, methods=["post"], url_path="revoke-all")
    def revoke_all(self, request):
        count = SessionService.revoke_all(user=request.user, actor=request.user, request=request)
        return success_response({"revoked_count": count})
