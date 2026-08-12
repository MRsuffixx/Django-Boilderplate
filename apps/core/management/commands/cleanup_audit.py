from django.core.management.base import BaseCommand

from apps.audit.tasks import cleanup_audit_logs


class Command(BaseCommand):
    help = "Apply configured audit retention; zero days retains logs indefinitely."

    def handle(self, *args, **options):
        self.stdout.write(f"Deleted {cleanup_audit_logs()} audit records.")
