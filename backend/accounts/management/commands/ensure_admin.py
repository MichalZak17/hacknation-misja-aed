from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update the admin login from ADMIN_EMAIL / ADMIN_PASSWORD in backend/.env"

    def handle(self, *args, **options):
        email = settings.ADMIN_EMAIL.strip().lower()
        User = get_user_model()
        user, created = User.objects.get_or_create(username=email, defaults={"email": email})
        user.email = email
        user.is_staff = user.is_superuser = user.is_active = True
        # Only re-hash when the password actually changed: set_password picks a new salt every time, and Django ties
        # sessions to the password hash, so re-hashing on every `npm run backend` would log everyone out.
        password_changed = not user.check_password(settings.ADMIN_PASSWORD)
        if password_changed:
            user.set_password(settings.ADMIN_PASSWORD)
        user.save()
        status = "created" if created else ("updated, password changed" if password_changed else "up to date")
        self.stdout.write(f"Admin {email} {status}")
