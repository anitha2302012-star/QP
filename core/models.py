from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", "admin")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLES = [("admin", "Admin"), ("faculty", "Faculty"), ("student", "Student")]
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=10, choices=ROLES, default="student")
    department = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return f"{self.name} ({self.role})"


EXAM_TYPES = [
    ("Internal 1", "Internal Assessment 1"),
    ("Internal 2", "Internal Assessment 2"),
    ("Internal 3", "Internal Assessment 3"),
    ("Model", "Model Exam"),
    ("Semester", "Semester Exam"),
]


def paper_path(instance, filename):
    return f"papers/{instance.academic_year}/{instance.department}/{filename}".replace(" ", "_")


class Paper(models.Model):
    department = models.CharField(max_length=80)
    regulation = models.CharField(max_length=20)
    academic_year = models.CharField(max_length=15, help_text="e.g. 2025-2026")
    semester = models.PositiveSmallIntegerField()
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=150)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES)
    file = models.FileField(upload_to=paper_path)
    file_hash = models.CharField(max_length=64, unique=True, editable=False)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="papers")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.subject_code} {self.subject_name} - {self.exam_type} ({self.academic_year})"

    def delete(self, *args, **kwargs):
        storage, name = self.file.storage, self.file.name
        super().delete(*args, **kwargs)
        if name:
            storage.delete(name)


class ActivityLog(models.Model):
    ACTIONS = [("LOGIN", "Login"), ("UPLOAD", "Upload"), ("VIEW", "View"),
               ("DOWNLOAD", "Download"), ("DELETE", "Delete")]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTIONS)
    paper = models.ForeignKey(Paper, on_delete=models.SET_NULL, null=True, blank=True)
    detail = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
