from rest_framework.permissions import BasePermission


class HasAPIKeyScope(BasePermission):
    def has_permission(self, request, view) -> bool:
        required = getattr(view, "required_api_key_scopes", ())
        api_key = getattr(request, "auth_api_key", None)
        if not api_key:
            return True
        return set(required).issubset(set(api_key.scopes))
