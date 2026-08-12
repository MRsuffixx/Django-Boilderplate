from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import (
    AccountStatus,
    User,
    UserBan,
    UserPreferences,
    UserProfile,
    UserSecuritySettings,
)
from apps.accounts.services import BanService
from apps.audit.services import AuditService
from common.admin import AuditAdminMixin


class SafeUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def clean_status(self):
        status = self.cleaned_data["status"]
        if status in {AccountStatus.BANNED, AccountStatus.DELETED}:
            raise ValidationError("Use the ban or account-deletion lifecycle service.")
        return status


class SafeUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "username", "status", "is_staff")


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 1
    max_num = 1


class UserPreferencesInline(admin.StackedInline):
    model = UserPreferences
    extra = 1
    max_num = 1


class UserSecuritySettingsInline(admin.StackedInline):
    model = UserSecuritySettings
    extra = 1
    max_num = 1
    readonly_fields = ["password_changed_at", "locked_until", "created_at", "updated_at"]


@admin.register(User)
class UserAdmin(AuditAdminMixin, BaseUserAdmin):
    form = SafeUserChangeForm
    add_form = SafeUserCreationForm
    ordering = ["-created_at"]
    list_display = [
        "email",
        "username",
        "status",
        "is_active",
        "is_staff",
        "email_verified_at",
        "created_at",
    ]
    list_filter = [
        "status",
        "is_active",
        "is_staff",
        "is_superuser",
        "email_verified_at",
        "created_at",
    ]
    search_fields = ["email", "username", "first_name", "last_name"]
    readonly_fields = [
        "id",
        "last_login",
        "last_login_ip",
        "date_joined",
        "created_at",
        "updated_at",
    ]
    fieldsets = [
        (None, {"fields": ["id", "email", "username", "password"]}),
        (_("Personal info"), {"fields": ["first_name", "last_name", "avatar", "phone"]}),
        (_("Verification"), {"fields": ["email_verified_at", "phone_verified_at"]}),
        (_("Account state"), {"fields": ["status", "is_active", "is_staff", "is_superuser"]}),
        (
            _("Django permissions"),
            {"fields": ["groups", "user_permissions"], "classes": ["collapse"]},
        ),
        (
            _("Important dates"),
            {"fields": ["last_login", "last_login_ip", "date_joined", "created_at", "updated_at"]},
        ),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "username", "password1", "password2", "status", "is_staff"],
            },
        )
    ]
    filter_horizontal = ["groups", "user_permissions"]
    inlines = [UserProfileInline, UserPreferencesInline, UserSecuritySettingsInline]

    def save_model(self, request, obj, form, change):
        before = User.objects.filter(pk=obj.pk).values("email", "status", "is_active").first()
        super().save_model(request, obj, form, change)
        if before and any(
            before[field] != getattr(obj, field) for field in ("email", "status", "is_active")
        ):
            from apps.authentication.services import SessionService, TokenService

            SessionService.revoke_all(user=obj, actor=request.user, request=request)
            TokenService.revoke_all_jwt(user=obj)

    def user_change_password(self, request, user_id, form_url=""):
        response = super().user_change_password(request, user_id, form_url)
        if request.method == "POST" and 300 <= response.status_code < 400:
            from apps.authentication.services import SessionService, TokenService
            from apps.security.models import SecurityEventType
            from apps.security.services import SecurityEventService

            user = User.objects.get(pk=user_id)
            SessionService.revoke_all(user=user, actor=request.user, request=request)
            TokenService.revoke_all_jwt(user=user)
            SecurityEventService.record(
                SecurityEventType.PASSWORD_CHANGED,
                user=user,
                request=request,
                metadata={"changed_by_admin": True},
            )
            AuditService.record(
                action="admin.password.changed",
                target=user,
                actor=request.user,
                request=request,
            )
        return response


@admin.register(UserBan)
class UserBanAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ["user", "banned_by", "starts_at", "expires_at", "revoked_at", "created_at"]
    list_filter = ["starts_at", "expires_at", "revoked_at"]
    search_fields = ["user__email", "user__username", "reason"]
    autocomplete_fields = ["user", "banned_by"]
    readonly_fields = ["id", "created_at", "revoked_at"]
    actions = ["revoke_selected"]

    def save_model(self, request, obj, form, change):
        if change:
            return super().save_model(request, obj, form, change)
        created = BanService.ban(
            user=obj.user,
            reason=obj.reason,
            actor=request.user,
            starts_at=obj.starts_at,
            expires_at=obj.expires_at,
            request=request,
        )
        obj.pk = created.pk
        obj._state.adding = False

    @admin.action(description="Revoke selected bans")
    def revoke_selected(self, request, queryset):
        for ban in queryset.filter(revoked_at__isnull=True):
            BanService.revoke(ban=ban, actor=request.user, request=request)
