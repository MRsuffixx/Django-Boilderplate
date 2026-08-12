import secrets

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Seed idempotent development data. Never creates demo accounts in production."

    def add_arguments(self, parser):
        parser.add_argument("--demo-admin", action="store_true", help="Create a development-only demo administrator")

    def handle(self, *args, **options):
        call_command("bootstrap")
        if not options["demo_admin"]:
            return
        if not settings.DEBUG or settings.APP_ENV == "production":
            raise CommandError("Demo users can only be created in a debug, non-production environment.")
        email = "admin@example.test"
        user = User.objects.filter(email=email).first()
        if user:
            self.stdout.write(f"Demo administrator already exists: {email}")
            return
        password = secrets.token_urlsafe(20)
        User.objects.create_superuser(email=email, username="demo-admin", password=password)
        self.stdout.write(self.style.WARNING(f"Created {email}; one-time generated password: {password}"))
