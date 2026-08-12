from rest_framework.permissions import BasePermission

from apps.authorization.services import PermissionService


class HasPermission(BasePermission):
    message = "You do not have the required permission."

    def has_permission(self, request, view) -> bool:
        codename = getattr(view, "required_permission", None)
        if not codename:
            raise RuntimeError(f"{view.__class__.__name__} must define required_permission")
        return PermissionService.has_permission(request.user, codename)


class IsOwnerOrHasPermission(HasPermission):
    """Reusable object check; views must opt into explicit ownership attribute names."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        owner_field = getattr(view, "owner_field", "user")
        owner = getattr(obj, owner_field, None)
        owner_id = getattr(obj, f"{owner_field}_id", None)
        if owner == request.user or owner_id == request.user.pk or obj == request.user:
            return True
        return super().has_permission(request, view)
