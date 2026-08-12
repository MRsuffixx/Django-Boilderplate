from django.conf import settings
from rest_framework import authentication, exceptions

from apps.accounts.models import AccountStatus
from apps.api_keys.services import APIKeyService
from common.utils.network import get_client_ip


class APIKeyAuthentication(authentication.BaseAuthentication):
    keyword = "X-API-Key"

    def authenticate(self, request):
        if not settings.ENABLE_API_KEYS:
            return None
        raw = request.headers.get(self.keyword)
        if not raw:
            return None
        api_key = APIKeyService.authenticate(raw, ip_address=get_client_ip(request))
        if not api_key:
            raise exceptions.AuthenticationFailed("Invalid API key.")
        if not api_key.owner.is_active or api_key.owner.status != AccountStatus.ACTIVE:
            raise exceptions.AuthenticationFailed("Invalid API key.")
        request.auth_api_key = api_key
        return api_key.owner, api_key
