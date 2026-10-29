from django.core.management.base import BaseCommand
from core.models import User


class Command(BaseCommand):
    help = "Create demo admin, faculty and student accounts"

    def handle(self, *args, **opts):
        demo = [
            ("admin@srit.ac.in", "Admin", "admin", "", "admin123"),
            ("faculty@srit.ac.in", "Demo Faculty", "faculty", "CSE", "faculty123"),
            ("student@srit.ac.in", "Demo Student", "student", "CSE", "student123"),
        ]
        for email, name, role, dept, pw in demo:
            if not User.objects.filter(email=email).exists():
                u = User.objects.create_user(email, pw, name=name, role=role, department=dept,
                                             is_staff=(role == "admin"), is_superuser=(role == "admin"))
                self.stdout.write(self.style.SUCCESS(f"Created {role}: {email} / {pw}"))
        self.stdout.write("Change these passwords before real use.")
