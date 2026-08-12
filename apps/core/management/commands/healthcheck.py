from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Check database and cache readiness."

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            cache.set("management-healthcheck", "ok", 5)
            if cache.get("management-healthcheck") != "ok":
                raise RuntimeError("Cache round trip failed")
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Database and cache are ready."))
