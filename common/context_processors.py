from django.conf import settings


def branding(_request):
    return {
        "APP_NAME": settings.APP_NAME,
        "SITE_NAME": settings.SITE_NAME,
        "SITE_URL": settings.SITE_URL,
        "SUPPORT_EMAIL": settings.SUPPORT_EMAIL,
    }
