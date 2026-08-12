from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuthorizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authorization"
    verbose_name = _("Authorization")
