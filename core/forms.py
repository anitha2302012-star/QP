import hashlib
from django import forms
from .models import Paper, User


class PaperForm(forms.ModelForm):
    class Meta:
        model = Paper
        fields = ["department", "regulation", "academic_year", "semester",
                  "subject_code", "subject_name", "exam_type", "file"]
        widgets = {"file": forms.ClearableFileInput(attrs={"accept": "application/pdf"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")
        self.fields["exam_type"].widget.attrs["class"] = "form-select"

    def clean_subject_code(self):
        return self.cleaned_data["subject_code"].strip().upper()

    def clean_semester(self):
        s = self.cleaned_data["semester"]
        if not 1 <= s <= 8:
            raise forms.ValidationError("Semester must be between 1 and 8.")
        return s

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are allowed.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File must be 10 MB or smaller.")
        head = f.read(5)
        f.seek(0)
        if head != b"%PDF-":
            raise forms.ValidationError("This does not look like a valid PDF.")
        h = hashlib.sha256()
        for chunk in f.chunks():
            h.update(chunk)
        f.seek(0)
        self._hash = h.hexdigest()
        if Paper.objects.filter(file_hash=self._hash).exists():
            raise forms.ValidationError("This exact PDF has already been uploaded (duplicate).")
        return f

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.file_hash = self._hash
        if commit:
            obj.save()
        return obj


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=6, required=False,
                               help_text="Leave blank to keep the current password when editing.")

    class Meta:
        model = User
        fields = ["name", "email", "role", "department", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for n, f in self.fields.items():
            f.widget.attrs["class"] = "form-check-input" if n == "is_active" else "form-control"
        self.fields["role"].widget.attrs["class"] = "form-select"

    def clean(self):
        data = super().clean()
        if not self.instance.pk and not data.get("password"):
            self.add_error("password", "Password is required for a new user.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = user.email.lower()
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        user.is_staff = user.role == "admin"
        if commit:
            user.save()
        return user
