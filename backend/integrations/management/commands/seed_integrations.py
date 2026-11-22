from django.core.management.base import BaseCommand

from integrations.connectors import REGISTRY
from integrations.models import Integration


class Command(BaseCommand):
    help = (
        "Create the built-in integrations (one per connector with a default) that don't exist yet, and apply every "
        "connector's declared priority and sync interval to its rows. Runs on every deploy."
    )

    def handle(self, *args, **options):
        for key, connector in REGISTRY.items():
            defaults = connector.default_integration
            if not defaults:
                continue
            defaults = dict(defaults)
            slug = defaults.pop("slug")
            _, created = Integration.objects.get_or_create(
                slug=slug,
                defaults={
                    **defaults,
                    "connector": key,
                    "format": connector.format,
                    "periodic_enabled": connector.periodic,
                },
            )
            if created:
                self.stdout.write(f"Created integration {slug}")
        for integration in Integration.objects.all():
            if integration.apply_connector_settings():
                integration.save()
                self.stdout.write(
                    f"{integration.slug}: priority {integration.priority}, every {integration.sync_interval_hours} h"
                )
