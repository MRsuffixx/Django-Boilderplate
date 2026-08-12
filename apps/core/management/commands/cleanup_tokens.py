from django.core.management.base import BaseCommand

from apps.authentication.tasks import cleanup_tokens


class Command(BaseCommand):
    help = "Remove expired one-time and JWT token records."

    def handle(self, *args, **options):
        self.stdout.write(f"Deleted {cleanup_tokens()} token records.")
