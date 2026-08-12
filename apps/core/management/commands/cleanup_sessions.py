from django.core.management.base import BaseCommand

from apps.authentication.tasks import cleanup_sessions


class Command(BaseCommand):
    help = "Remove revoked sessions older than the configured retention period."

    def handle(self, *args, **options):
        self.stdout.write(f"Deleted {cleanup_sessions()} session records.")
