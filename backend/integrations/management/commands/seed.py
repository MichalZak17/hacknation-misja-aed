from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "One-time seed: create the built-in integrations and run each one's historical sync"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Repeat historical syncs that already ran")

    def handle(self, *args, force, **options):
        call_command("seed_integrations")
        call_command("sync", all=True, historical=True, force=force, trigger="seed")
        from devices.exports import rebuild_all

        rebuild_all()
        self.stdout.write("Exports rebuilt in var/exports/")
