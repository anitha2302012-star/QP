from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import PaperForm, UserForm
from .models import ActivityLog, EXAM_TYPES, Paper, User


def log(user, action, paper=None, detail=""):
    ActivityLog.objects.create(user=user, action=action, paper=paper, detail=detail)


def role_required(*roles):
    def deco(view):
        @wraps(view)
        @login_required
        def wrapper(request, *a, **kw):
            if request.user.role not in roles:
                raise PermissionDenied
            return view(request, *a, **kw)
        return wrapper
    return deco


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("email", "").strip().lower(),
                            password=request.POST.get("password", ""))
        if user:
            login(request, user)
            log(user, "LOGIN")
            return redirect(request.GET.get("next") or "home")
        messages.error(request, "Invalid email or password (or account disabled).")
    return render(request, "core/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def home(request):
    ctx = {"recent": Paper.objects.all()[:6]}
    if request.user.role == "faculty":
        ctx["my_count"] = request.user.papers.count()
    if request.user.role == "admin":
        ctx.update(papers=Paper.objects.count(), users=User.objects.count(),
                   downloads=ActivityLog.objects.filter(action="DOWNLOAD").count(),
                   uploads=ActivityLog.objects.filter(action="UPLOAD").count())
    return render(request, "core/home.html", ctx)


def filtered_papers(request):
    qs = Paper.objects.select_related("uploaded_by")
    q = request.GET.get("q", "").strip()
    for word in q.split():
        qs = qs.filter(Q(subject_name__icontains=word) | Q(subject_code__icontains=word) |
                       Q(department__icontains=word) | Q(regulation__icontains=word) |
                       Q(academic_year__icontains=word) | Q(exam_type__icontains=word))
    for field in ("department", "regulation", "academic_year", "semester", "exam_type"):
        val = request.GET.get(field, "").strip()
        if val:
            qs = qs.filter(**{field: val})
    return qs


@login_required
def search(request):
    qs = filtered_papers(request)
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    distinct = lambda f: Paper.objects.order_by(f).values_list(f, flat=True).distinct()
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "core/search.html", {
        "page": page, "params": params.urlencode(), "get": request.GET,
        "departments": distinct("department"), "regulations": distinct("regulation"),
        "years": distinct("academic_year"), "exam_types": EXAM_TYPES,
        "semesters": range(1, 9),
    })


@login_required
def detail(request, pk):
    paper = get_object_or_404(Paper, pk=pk)
    log(request.user, "VIEW", paper)
    related = Paper.objects.filter(
        Q(subject_code=paper.subject_code) | Q(subject_name__iexact=paper.subject_name)
    ).exclude(pk=paper.pk)[:6]
    can_delete = request.user.role == "admin" or paper.uploaded_by_id == request.user.id
    return render(request, "core/detail.html", {"paper": paper, "related": related, "can_delete": can_delete})


@login_required
def download(request, pk):
    paper = get_object_or_404(Paper, pk=pk)
    inline = request.GET.get("inline") == "1"
    log(request.user, "VIEW" if inline else "DOWNLOAD", paper)
    name = f"{paper.subject_code}_{paper.exam_type}_{paper.academic_year}.pdf".replace(" ", "_")
    return FileResponse(paper.file.open("rb"), as_attachment=not inline,
                        filename=name, content_type="application/pdf")


@role_required("faculty", "admin")
def upload(request):
    form = PaperForm(request.POST or None, request.FILES or None,
                     initial={"department": request.user.department})
    if request.method == "POST" and form.is_valid():
        paper = form.save(commit=False)
        paper.uploaded_by = request.user
        paper.save()
        log(request.user, "UPLOAD", paper)
        messages.success(request, "Question paper uploaded successfully.")
        return redirect("detail", pk=paper.pk)
    return render(request, "core/upload.html", {"form": form})


@role_required("faculty")
def my_uploads(request):
    return render(request, "core/my_uploads.html", {"papers": request.user.papers.all()})


@login_required
def delete_paper(request, pk):
    paper = get_object_or_404(Paper, pk=pk)
    if not (request.user.role == "admin" or
            (request.user.role == "faculty" and paper.uploaded_by_id == request.user.id)):
        raise PermissionDenied
    if request.method == "POST":
        log(request.user, "DELETE", None, detail=str(paper))
        paper.delete()
        messages.success(request, "Question paper deleted.")
        return redirect("search")
    return render(request, "core/confirm_delete.html", {"obj": paper, "kind": "question paper"})


# ---------------- Admin ----------------
@role_required("admin")
def users_list(request):
    return render(request, "core/users.html", {"users": User.objects.annotate(n=Count("papers"))})


@role_required("admin")
def user_edit(request, pk=None):
    instance = get_object_or_404(User, pk=pk) if pk else None
    form = UserForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        if instance and instance.pk == request.user.pk and not form.cleaned_data["is_active"]:
            messages.error(request, "You cannot disable your own account.")
        else:
            form.save()
            messages.success(request, "User saved.")
            return redirect("users")
    return render(request, "core/user_form.html", {"form": form, "editing": bool(instance)})


@role_required("admin")
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("users")
    if request.method == "POST":
        user.delete()
        messages.success(request, "User deleted.")
        return redirect("users")
    return render(request, "core/confirm_delete.html", {"obj": user, "kind": "user"})


@role_required("admin")
def analytics(request):
    logs = ActivityLog.objects.select_related("user", "paper")
    today = timezone.localdate()
    ctx = {
        "total_papers": Paper.objects.count(),
        "by_role": User.objects.values("role").annotate(n=Count("id")),
        "uploads": logs.filter(action="UPLOAD").count(),
        "downloads": logs.filter(action="DOWNLOAD").count(),
        "views": logs.filter(action="VIEW").count(),
        "today": logs.filter(timestamp__date=today).count(),
        "top": Paper.objects.annotate(d=Count("activitylog", filter=Q(activitylog__action="DOWNLOAD")))
                    .filter(d__gt=0).order_by("-d")[:5],
        "by_dept": Paper.objects.values("department").annotate(n=Count("id")).order_by("-n"),
        "recent": logs[:30],
    }
    return render(request, "core/analytics.html", ctx)


@role_required("admin")
def all_papers(request):
    return render(request, "core/my_uploads.html", {"papers": Paper.objects.select_related("uploaded_by"),
                                                    "admin_view": True})
