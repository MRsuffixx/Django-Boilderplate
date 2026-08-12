from datetime import timedelta

from django.utils import timezone

from apps.authentication.services import SessionService


class UserSessionMiddleware:
    touch_interval = timedelta(minutes=5)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            getattr(request, "user", None)
            and request.user.is_authenticated
            and request.session.session_key
        ):
            if not request.user.can_authenticate_now():
                request.session.flush()
                return self.get_response(request)
            user_session = SessionService.current(request)
            if user_session and user_session.revoked_at:
                request.session.flush()
            elif (
                user_session
                and user_session.last_activity_at < timezone.now() - self.touch_interval
            ):
                user_session.save(update_fields=["last_activity_at"])
        return self.get_response(request)
