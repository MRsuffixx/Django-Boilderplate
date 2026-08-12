from django.db import transaction
from rest_framework import generics, viewsets

from apps.accounts.models import User, UserPreferences, UserProfile
from apps.api.serializers.accounts import (
    SecurityEventSerializer,
    UserAdminSerializer,
    UserPreferencesSerializer,
    UserProfileSerializer,
    UserSerializer,
)
from apps.api_keys.permissions import HasAPIKeyScope
from apps.audit.services import AuditService
from common.permissions import HasPermission
from common.responses import success_response


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    required_api_key_scopes = ("profile.read",)

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)


class CurrentUserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    required_api_key_scopes_by_method = {
        "GET": ("profile.read",),
        "PUT": ("profile.write",),
        "PATCH": ("profile.write",),
    }

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return success_response(response.data)


class CurrentUserPreferencesView(generics.RetrieveUpdateAPIView):
    serializer_class = UserPreferencesSerializer
    required_api_key_scopes_by_method = {
        "GET": ("profile.read",),
        "PUT": ("profile.write",),
        "PATCH": ("profile.write",),
    }

    def get_object(self):
        preferences, _ = UserPreferences.objects.get_or_create(user=self.request.user)
        return preferences

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return success_response(response.data)


class SecurityEventListView(generics.ListAPIView):
    serializer_class = SecurityEventSerializer
    ordering_fields = ["created_at", "event_type"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return self.request.user.security_events.all()


class UserAdminViewSet(viewsets.ModelViewSet):
    serializer_class = UserAdminSerializer
    permission_classes = [HasPermission, HasAPIKeyScope]
    filterset_fields = ["status", "is_active", "is_staff"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering_fields = ["created_at", "email", "username", "last_login"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return User.objects.all().select_related("profile", "preferences", "security_settings")

    @property
    def required_permission(self):
        return {
            "list": "users.view",
            "retrieve": "users.view",
            "create": "users.create",
            "update": "users.update",
            "partial_update": "users.update",
            "destroy": "users.delete",
        }.get(self.action, "users.view")

    def perform_create(self, serializer):
        from common.exceptions import APIException

        raise APIException(
            "Use the registration or administrative account service.",
            code="METHOD_NOT_ALLOWED",
            status_code=405,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        before = {field: getattr(serializer.instance, field) for field in serializer.validated_data}
        user = serializer.save()
        AuditService.record(
            action="user.updated",
            target=user,
            actor=self.request.user,
            request=self.request,
            before=before,
            after=serializer.validated_data,
        )

    def destroy(self, request, *args, **kwargs):
        from common.exceptions import APIException

        raise APIException(
            "Use the account deletion service.", code="METHOD_NOT_ALLOWED", status_code=405
        )
