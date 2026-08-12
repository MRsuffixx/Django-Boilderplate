from django.core.management.base import BaseCommand

from apps.security.tasks import cleanup_login_attempts


class Command(BaseCommand):
    help = "Delete expired database-backed login throttle counters"

    def handle(self, *args, **options):
        deleted = cleanup_login_attempts()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} login throttle records"))
