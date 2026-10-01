import json
from datetime import date
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q, Max
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Category,
    SiteSettings,
    SocialLink,
    Task,
    UserProfile,
    validate_hex_color,
)

User = get_user_model()


def _profile_for(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if not profile.categories_seeded:
        Category.objects.bulk_create(
            [Category(user=user, name=name) for name, _ in Task.CATEGORY_CHOICES],
            ignore_conflicts=True,
        )
        profile.categories_seeded = True
        profile.save(update_fields=["categories_seeded"])
    return profile


def _task_values(request, task=None, user=None):
    priorities = {value for value, _ in Task.PRIORITY_CHOICES}
    categories = (
        {value for value, _ in _category_choices(user)} if user is not None else set()
    )
    colors = request.POST.get("color", "#d46b32")
    try:
        validate_hex_color(colors)
    except ValidationError:
        colors = "#d46b32"
    category = (
        request.POST.get("category", "").strip()
        if request.POST.get("category", "").strip() in categories
        else ""
    )
    values = {
        "task": request.POST.get("task", "").strip(),
        "description": request.POST.get("description", "").strip(),
        "priority": (
            request.POST.get("priority", "medium")
            if request.POST.get("priority") in priorities
            else "medium"
        ),
        "category": category[:50],
        "due_date": (
            parse_date(request.POST.get("due_date"))
            if request.POST.get("due_date")
            else None
        ),
        "color": colors,
    }
    if task is not None:
        values["is_favorite"] = request.POST.get("is_favorite") == "on"
    return values


def _category_choices(user):
    _profile_for(user)
    return [
        (category.name, category.name.title())
        for category in Category.objects.filter(user=user)
    ]


def _task_context(user):
    return {
        "profile": _profile_for(user),
        "categories": _category_choices(user),
        "task_colors": Task.COLOR_CHOICES,
    }


@login_required
def home(request):
    profile = _profile_for(request.user)
    tasks = Task.objects.filter(user=request.user)
    search = request.GET.get("q", "").strip()
    selected_filter = request.GET.get("filter", "all")
    if search:
        tasks = tasks.filter(
            Q(task__icontains=search) | Q(description__icontains=search)
        )
    if selected_filter == "active":
        tasks = tasks.filter(is_completed=False)
    elif selected_filter == "completed":
        tasks = tasks.filter(is_completed=True)
    elif selected_filter == "starred":
        tasks = tasks.filter(is_favorite=True)
    elif selected_filter == "overdue":
        tasks = tasks.filter(is_completed=False, due_date__lt=date.today())
    elif selected_filter in {"high", "medium", "low"}:
        tasks = tasks.filter(priority=selected_filter)
    all_tasks = Task.objects.filter(user=request.user)
    context = {
        "tasks": tasks.order_by("position", "-updated_at"),
        "profile": profile,
        "search": search,
        "selected_filter": selected_filter,
        "total_count": all_tasks.count(),
        "completed_count": all_tasks.filter(is_completed=True).count(),
        "pending_count": all_tasks.filter(is_completed=False).count(),
        "overdue_count": all_tasks.filter(
            is_completed=False, due_date__lt=date.today()
        ).count(),
        "high_count": all_tasks.filter(priority="high", is_completed=False).count(),
        "task_colors": Task.COLOR_CHOICES,
        "filter_options": (
            ("all", "All"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("overdue", "Overdue"),
            ("starred", "Starred"),
        ),
        "categories": _category_choices(request.user),
    }
    return render(request, "home.html", context)


@login_required
def add_task_page(request):
    return render(
        request,
        "task_form.html",
        {**_task_context(request.user), "page_title": "Add task"},
    )


@login_required
def addTask(request):
    if request.method == "POST":
        values = _task_values(request, user=request.user)
        if values["task"]:
            profile = _profile_for(request.user)
            if not request.POST.get("priority"):
                values["priority"] = profile.default_priority
            if not request.POST.get("color"):
                values["color"] = profile.default_task_color
            max_position = Task.objects.filter(user=request.user).aggregate(
                Max("position")
            )["position__max"]
            values["position"] = (max_position + 1) if max_position is not None else 0
            Task.objects.create(user=request.user, **values)
    return redirect("home")


@login_required
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == "POST":
        values = _task_values(request, task, request.user)
        if values["task"]:
            for key, value in values.items():
                setattr(task, key, value)
            task.save()
            return redirect("task_detail", pk=task.pk)
    return render(
        request,
        "edit_task.html",
        {
            "task": task,
            **_task_context(request.user),
            "priorities": Task.PRIORITY_CHOICES,
        },
    )


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    return render(
        request,
        "task_detail.html",
        {"task": task, "profile": _profile_for(request.user)},
    )


@login_required
def mark_as_done(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.is_completed = True
    task.save(update_fields=["is_completed", "updated_at"])
    return redirect("home")


@login_required
def mark_as_undone(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.is_completed = False
    task.save(update_fields=["is_completed", "updated_at"])
    return redirect("home")


@require_POST
@login_required
def toggle_favorite(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.is_favorite = not task.is_favorite
    task.save(update_fields=["is_favorite", "updated_at"])
    return redirect(request.POST.get("next") or "home")


@require_POST
@login_required
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.delete()
    return redirect("home")


@require_POST
@login_required
def reorder_tasks(request):
    try:
        task_ids = json.loads(request.body).get("task_ids", [])
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid task order."}, status=400)
    owned_tasks = {
        str(task.pk): task
        for task in Task.objects.filter(user=request.user, pk__in=task_ids)
    }
    for position, task_id in enumerate(task_ids):
        task = owned_tasks.get(str(task_id))
        if task:
            task.position = position
            task.save(update_fields=["position"])
    return JsonResponse({"ok": True})


@login_required
def profile_settings(request):
    profile = _profile_for(request.user)
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if (
            email
            and request.user.__class__.objects.filter(email__iexact=email)
            .exclude(pk=request.user.pk)
            .exists()
        ):
            messages.error(request, "That email is already in use.")
        else:
            request.user.first_name = request.POST.get("first_name", "").strip()
            request.user.last_name = request.POST.get("last_name", "").strip()
            if email:
                request.user.email = email
                request.user.username = email
            request.user.save(
                update_fields=["first_name", "last_name", "email", "username"]
            )
            background_colors = {value for value, _ in UserProfile.BACKGROUND_CHOICES}
            accent_colors = {value for value, _ in UserProfile.ACCENT_CHOICES}
            task_colors = {value for value, _ in Task.COLOR_CHOICES}
            priorities = {value for value, _ in Task.PRIORITY_CHOICES}
            try:
                validate_hex_color(
                    request.POST.get("background_color", profile.background_color)
                )
                validate_hex_color(
                    request.POST.get("accent_color", profile.accent_color)
                )
                validate_hex_color(
                    request.POST.get("surface_color", profile.surface_color)
                )
                validate_hex_color(
                    request.POST.get("default_task_color", profile.default_task_color)
                )
            except ValidationError:
                messages.error(
                    request, "Choose valid colors for your appearance settings."
                )
                return render(
                    request,
                    "profile.html",
                    {
                        "profile": profile,
                        "background_colors": UserProfile.BACKGROUND_CHOICES,
                        "accent_colors": UserProfile.ACCENT_CHOICES,
                        "task_colors": Task.COLOR_CHOICES,
                        "categories": _category_choices(request.user),
                    },
                )
            profile.background_color = request.POST.get(
                "background_color", profile.background_color
            )
            profile.accent_color = request.POST.get(
                "accent_color", profile.accent_color
            )
            profile.surface_color = request.POST.get(
                "surface_color", profile.surface_color
            )
            profile.default_task_color = request.POST.get(
                "default_task_color", profile.default_task_color
            )
            profile.default_priority = (
                request.POST.get("default_priority")
                if request.POST.get("default_priority") in priorities
                else profile.default_priority
            )
            if request.FILES.get("profile_picture"):
                if profile.profile_picture:
                    profile.profile_picture.delete(save=False)
                profile.profile_picture = request.FILES["profile_picture"]
            if request.FILES.get("background_image"):
                if profile.background_image:
                    profile.background_image.delete(save=False)
                profile.background_image = request.FILES["background_image"]
            if request.POST.get("remove_profile_picture") == "on":
                profile.profile_picture.delete(save=False)
                profile.profile_picture = None
            if request.POST.get("remove_background_image") == "on":
                profile.background_image.delete(save=False)
                profile.background_image = None
            try:
                profile.full_clean()
                profile.save()
            except ValidationError as error:
                messages.error(request, error.messages[0])
                return render(request, "profile.html", {"profile": profile})
            messages.success(request, "Settings saved.")
            return redirect("profile")
    return render(
        request,
        "profile.html",
        {
            "profile": profile,
            "background_colors": UserProfile.BACKGROUND_CHOICES,
            "accent_colors": UserProfile.ACCENT_CHOICES,
            "task_colors": Task.COLOR_CHOICES,
            "categories": _category_choices(request.user),
        },
    )


@require_POST
@login_required
def add_category(request):
    name = request.POST.get("name", "").strip()[:50]
    if name:
        Category.objects.get_or_create(user=request.user, name=name)
    return redirect("profile")


@require_POST
@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    Task.objects.filter(user=request.user, category=category.name).update(category="")
    category.delete()
    return redirect("profile")


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapped


@admin_required
def admin_dashboard(request):
    recent = timezone.now() - timedelta(days=30)
    users = User.objects.all()
    tasks = Task.objects.all()
    return render(
        request,
        "admin_dashboard.html",
        {
            "total_users": users.count(),
            "active_users": users.filter(
                is_active=True, last_login__gte=recent
            ).count(),
            "total_tasks": tasks.count(),
            "completed_tasks": tasks.filter(is_completed=True).count(),
            "pending_tasks": tasks.filter(is_completed=False).count(),
        },
    )


@admin_required
def admin_users(request):
    users = User.objects.all().order_by("-date_joined")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    if status == "active":
        users = users.filter(is_active=True)
    elif status == "inactive":
        users = users.filter(is_active=False)
    return render(
        request, "admin_users.html", {"users": users, "query": query, "status": status}
    )


@admin_required
def admin_settings(request):
    return redirect("admin_customization")


@admin_required
def admin_customization(request):
    settings, _ = SiteSettings.objects.get_or_create(pk=1)
    if request.method == "POST":
        settings.website_name = request.POST.get("website_name", "").strip() or "Daymark"
        settings.homepage_quote = request.POST.get("homepage_quote", "").strip()
        settings.footer_description = request.POST.get("footer_description", "").strip()
        settings.contact_email = request.POST.get("contact_email", "").strip()
        try:
            settings.full_clean()
            settings.save()
            messages.success(request, "Website customization saved.")
            return redirect("admin_customization")
        except ValidationError as error:
            messages.error(request, error.messages[0])
    return render(request, "admin_customization.html", {"site_settings": settings})


@admin_required
def admin_social(request):
    if request.method == "POST":
        link_id = request.POST.get("link_id")
        link = get_object_or_404(SocialLink, pk=link_id) if link_id else SocialLink()
        link.platform = request.POST.get("platform", "other")
        link.url = request.POST.get("url", "").strip()
        link.is_active = request.POST.get("is_active") == "on"
        link.position = int(request.POST.get("position") or 0)
        try:
            link.full_clean()
            link.save()
            messages.success(request, "Social link saved.")
            return redirect("admin_social")
        except (ValidationError, ValueError) as error:
            message = error.messages[0] if hasattr(error, "messages") else "Enter a valid position."
            messages.error(request, message)
    return render(
        request,
        "admin_social.html",
        {"social_links": SocialLink.objects.all(), "platforms": SocialLink.PLATFORM_CHOICES},
    )


@admin_required
@require_POST
def delete_social(request, pk):
    get_object_or_404(SocialLink, pk=pk).delete()
    return redirect("admin_social")


@admin_required
@require_POST
def toggle_social(request, pk):
    link = get_object_or_404(SocialLink, pk=pk)
    link.is_active = not link.is_active
    link.save(update_fields=["is_active"])
    return redirect("admin_social")


@admin_required
def view_website(request):
    return redirect("home")


@login_required
def protected_profile_picture(request):
    profile = _profile_for(request.user)
    if not profile.profile_picture:
        raise Http404
    return FileResponse(profile.profile_picture.open("rb"), content_type="image/*")


@login_required
def protected_background_image(request):
    profile = _profile_for(request.user)
    if not profile.background_image:
        raise Http404
    return FileResponse(profile.background_image.open("rb"), content_type="image/*")
