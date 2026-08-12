from django.core.management.base import BaseCommand

from apps.notifications.tasks import cleanup_notifications


class Command(BaseCommand):
    help = "Remove expired/read notifications according to configured retention."

    def handle(self, *args, **options):
        self.stdout.write(f"Deleted {cleanup_notifications()} notification records.")
