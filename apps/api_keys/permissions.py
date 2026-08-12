from rest_framework.permissions import BasePermission


class HasAPIKeyScope(BasePermission):
    def has_permission(self, request, view) -> bool:
        api_key = getattr(request, "auth_api_key", None)
        if not api_key:
            return True
        by_method = getattr(view, "required_api_key_scopes_by_method", None)
        declared = hasattr(view, "required_api_key_scopes") or by_method is not None
        if not declared:
            return False
        required = (
            by_method.get(request.method, ())
            if by_method is not None
            else getattr(view, "required_api_key_scopes", ())
        )
        return set(required).issubset(set(api_key.scopes))
