from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from apps.accounts.models import User


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email")
        if not identifier or not password:
            return None
        try:
            user = User.objects.get(
                Q(email__iexact=identifier.strip()) | Q(username__iexact=identifier.strip())
            )
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
