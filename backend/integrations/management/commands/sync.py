from django.core.management.base import BaseCommand, CommandError

from integrations.engine import SyncRefused, execute_run
from integrations.models import Integration, SyncRun


class Command(BaseCommand):
    help = "Run a sync now, in this process. `sync osm-poland --historical`, `sync --all --dry-run`"

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*")
        parser.add_argument("--all", action="store_true", help="Every enabled integration")
        parser.add_argument("--historical", action="store_true")
        parser.add_argument("--dry-run", action="store_true", help="Fetch, parse, validate and diff; write nothing")
        parser.add_argument("--force", action="store_true", help="Repeat a historical sync that already ran")
        parser.add_argument(
            "--reextract", action="store_true", help="Ask the LLM again for every record with text, ignoring its cache"
        )
        parser.add_argument("--trigger", default=SyncRun.Trigger.MANUAL, choices=SyncRun.Trigger.values)

    def handle(self, *args, slugs, all, historical, dry_run, force, reextract, trigger, **options):
        if all:
            integrations = list(Integration.objects.filter(enabled=True).order_by("priority"))
        else:
            integrations = list(Integration.objects.filter(slug__in=slugs).order_by("priority"))
            missing = set(slugs) - {i.slug for i in integrations}
            if missing:
                raise CommandError(f"Unknown integrations: {', '.join(sorted(missing))}")
        if not integrations:
            raise CommandError("Name integrations or pass --all")
        if reextract and dry_run:
            raise CommandError("--reextract writes the new answers, so it can't be combined with --dry-run")
        kind = SyncRun.Kind.HISTORICAL if historical else SyncRun.Kind.PERIODIC
        failed = False
        for integration in integrations:
            if integration.connector == "operator_file" and not integration.config.get("file_path"):
                self.stdout.write(f"{integration.slug}: skipped (no file uploaded)")
                continue
            if kind == SyncRun.Kind.HISTORICAL and integration.historical_completed_at and not (force or dry_run):
                self.stdout.write(f"{integration.slug}: historical sync already done (use --force)")
                continue
            if integration.runs.filter(status__in=["queued", "running"]).exists():
                raise CommandError(f"{integration.slug}: a sync is already queued or running")
            run = SyncRun.objects.create(
                integration=integration, kind=kind, trigger=trigger, dry_run=dry_run, force=force, reextract=reextract
            )
            try:
                run = execute_run(run.pk)
            except SyncRefused as exc:
                raise CommandError(str(exc)) from exc
            failed |= run.status != SyncRun.Status.SUCCESS
            self.stdout.write(
                f"{integration.slug}: {run.status}{' (dry run)' if dry_run else ''} — fetched {run.fetched}, "
                f"created {run.created}, updated {run.updated}, unchanged {run.unchanged}, removed {run.removed}, "
                f"invalid {run.invalid}, {run.duration_ms} ms" + (f" — {run.error}" if run.error else "")
            )
        if failed:
            raise CommandError("Some syncs failed")
