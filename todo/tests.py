from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from io import BytesIO
from PIL import Image
from datetime import date, timedelta

from .models import Category, EmailOTP, SocialLink, Task


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthenticationTests(TestCase):
    def test_root_is_login_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")

    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")

    def test_registration_requires_otp_then_logs_user_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "password": "Abc!1234",
                "confirmation": "Abc!1234",
            },
        )
        self.assertRedirects(response, reverse("verify_registration"))
        user = User.objects.get(email="ada@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ada@example.com"])
        otp = EmailOTP.objects.get(user=user, purpose=EmailOTP.PURPOSE_REGISTRATION)
        response = self.client.post(reverse("verify_registration"), {"otp": otp.code})
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.get(pk=user.pk).is_active)
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_registration_rejects_invalid_passwords(self):
        invalid_passwords = ("abc!1234", "ABC!1234", "Abc12345", "Abc!12345")
        for index, password in enumerate(invalid_passwords):
            response = self.client.post(
                reverse("register"),
                {
                    "first_name": "Ada",
                    "last_name": "Lovelace",
                    "email": f"invalid-{index}@example.com",
                    "password": password,
                    "confirmation": password,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Password must be at most 8 characters")

    def test_forgot_password_requires_otp(self):
        user = User.objects.create_user(
            "ada@example.com", "ada@example.com", "old-password", is_active=True
        )
        self.client.post(reverse("forgot_password"), {"email": user.email})
        otp = EmailOTP.objects.get(user=user, purpose=EmailOTP.PURPOSE_PASSWORD_RESET)
        self.client.post(reverse("verify_password_reset"), {"otp": otp.code})
        response = self.client.post(
            reverse("reset_password", args=[user.id]),
            {
                "password": "new-password-123",
                "confirmation": "new-password-123",
            },
        )
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(
            self.client.login(username=user.email, password="new-password-123")
        )

    def test_profile_id_is_not_changed_by_profile_update(self):
        user = User.objects.create_user(
            "ada@example.com",
            "ada@example.com",
            "password-123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Augusta",
                "last_name": "King",
                "email": user.email,
                "id": "999999",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        user.refresh_from_db()
        self.assertEqual(user.pk, user.id)
        self.assertEqual(user.first_name, "Augusta")

    def test_tasks_are_private_to_their_owner(self):
        first = User.objects.create_user(
            "first@example.com", "first@example.com", "password-123", is_active=True
        )
        second = User.objects.create_user(
            "second@example.com", "second@example.com", "password-123", is_active=True
        )
        task = Task.objects.create(user=first, task="Private task")
        self.client.force_login(second)
        self.assertEqual(
            self.client.get(reverse("edit_task", args=[task.pk])).status_code, 404
        )


class TaskFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "owner@example.com", "owner@example.com", "Password-123", is_active=True
        )
        self.other_user = User.objects.create_user(
            "other@example.com", "other@example.com", "Password-123", is_active=True
        )
        self.client.force_login(self.user)

    def test_create_task_metadata_and_dashboard(self):
        response = self.client.post(
            reverse("addTask"),
            {
                "task": "Finish FYP",
                "description": "Write the final documentation.",
                "priority": "high",
                "category": "study",
                "due_date": str(date.today()),
                "color": "#d94c4c",
            },
        )
        self.assertRedirects(response, reverse("home"))
        task = Task.objects.get(user=self.user)
        self.assertEqual(task.priority, "high")
        self.assertEqual(task.category, "study")
        self.assertContains(self.client.get(reverse("home")), "Finish FYP")

    def test_task_and_profile_pages_render(self):
        task = Task.objects.create(user=self.user, task="Read detail")
        self.assertEqual(
            self.client.get(reverse("task_detail", args=[task.pk])).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("edit_task", args=[task.pk])).status_code, 200
        )
        self.assertEqual(self.client.get(reverse("profile")).status_code, 200)

    def test_search_and_filter_are_user_scoped(self):
        Task.objects.create(
            user=self.user,
            task="Visible study",
            description="research",
            priority="high",
        )
        Task.objects.create(
            user=self.other_user,
            task="Private study",
            description="research",
            priority="high",
        )
        response = self.client.get(reverse("home"), {"q": "study", "filter": "high"})
        self.assertContains(response, "Visible study")
        self.assertNotContains(response, "Private study")

    def test_detail_and_reorder_require_ownership(self):
        first = Task.objects.create(user=self.user, task="First", position=0)
        second = Task.objects.create(user=self.user, task="Second", position=1)
        foreign = Task.objects.create(user=self.other_user, task="Private")
        response = self.client.post(
            reverse("reorder_tasks"),
            data='{"task_ids": [%d, %d, %d]}' % (second.pk, foreign.pk, first.pk),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((second.position, first.position), (0, 2))
        self.assertEqual(
            self.client.get(reverse("task_detail", args=[foreign.pk])).status_code, 404
        )

    def test_profile_appearance_and_image_persist(self):
        image_buffer = BytesIO()
        Image.new("RGB", (20, 20), "red").save(image_buffer, format="PNG")
        image = SimpleUploadedFile(
            "avatar.png", image_buffer.getvalue(), content_type="image/png"
        )
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Owner",
                "last_name": "Person",
                "email": self.user.email,
                "background_color": "#dcecf7",
                "accent_color": "#287f7c",
                "default_task_color": "#4285b5",
                "default_priority": "high",
                "profile_picture": image,
            },
        )
        self.assertRedirects(response, reverse("profile"))
        profile = self.user.profile_settings
        self.assertEqual(profile.background_color, "#dcecf7")
        self.assertEqual(profile.accent_color, "#287f7c")
        self.assertTrue(profile.profile_picture)
        self.assertEqual(self.client.get(reverse("profile_picture")).status_code, 200)

    def test_due_date_and_completion_filters(self):
        Task.objects.create(
            user=self.user, task="Late", due_date=date.today() - timedelta(days=1)
        )
        Task.objects.create(user=self.user, task="Done", is_completed=True)
        response = self.client.get(reverse("home"), {"filter": "overdue"})
        self.assertContains(response, "Late")
        self.assertEqual(
            list(response.context["tasks"].values_list("task", flat=True)), ["Late"]
        )

    def test_custom_category_delete_untags_but_keeps_tasks(self):
        self.client.post(reverse("add_category"), {"name": "FYP"})
        category = Category.objects.get(user=self.user, name="FYP")
        task = Task.objects.create(user=self.user, task="Documentation", category="FYP")
        response = self.client.post(reverse("delete_category", args=[category.pk]))
        self.assertRedirects(response, reverse("profile"))
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())
        task.refresh_from_db()
        self.assertEqual(task.category, "")

    def test_custom_colors_persist_and_add_page_is_separate(self):
        response = self.client.get(reverse("add_task_page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="color"')
        self.client.post(
            reverse("profile"),
            {
                "first_name": "Owner",
                "last_name": "Person",
                "email": self.user.email,
                "background_color": "#123456",
                "accent_color": "#abcdef",
                "surface_color": "#334455",
                "default_task_color": "#fedcba",
                "default_priority": "low",
            },
        )
        profile = self.user.profile_settings
        self.assertEqual(
            (profile.background_color, profile.accent_color, profile.surface_color),
            ("#123456", "#abcdef", "#334455"),
        )
        self.client.post(
            reverse("addTask"),
            {"task": "Colored", "color": "#102030", "priority": "low"},
        )
        self.assertEqual(Task.objects.get(task="Colored").color, "#102030")

    def test_admin_role_redirect_and_protection(self):
        admin = User.objects.create_superuser(
            "admin@example.com", "admin@example.com", "Admin!123"
        )
        self.client.logout()
        response = self.client.post(
            reverse("login"), {"email": admin.email, "password": "Admin!123"}
        )
        self.assertRedirects(response, reverse("admin_dashboard"))
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.get(reverse("admin_dashboard")), reverse("home")
        )
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin_users")).status_code, 200)

    def test_statistic_filter_links_filter_owned_tasks(self):
        Task.objects.create(user=self.user, task="Pending task", is_completed=False)
        Task.objects.create(user=self.user, task="Completed task", is_completed=True)
        response = self.client.get(reverse("home"), {"filter": "completed"})
        self.assertEqual(
            list(response.context["tasks"].values_list("task", flat=True)),
            ["Completed task"],
        )

    def test_admin_customization_and_social_deactivation(self):
        admin = User.objects.create_superuser(
            "site-admin@example.com", "site-admin@example.com", "Admin!123"
        )
        self.client.force_login(admin)
        response = self.client.post(
            reverse("admin_customization"),
            {
                "website_name": "New Daymark",
                "homepage_quote": "A new quote.",
                "footer_description": "A new footer.",
                "contact_email": "hello@example.com",
            },
        )
        self.assertRedirects(response, reverse("admin_customization"))
        self.client.post(
            reverse("admin_social"),
            {
                "platform": "instagram",
                "url": "https://instagram.com/daymark",
                "is_active": "on",
                "position": "0",
            },
        )
        link = SocialLink.objects.get(platform="instagram")
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "New Daymark")
        self.assertContains(response, "A new quote.")
        self.assertContains(response, link.url)
        self.client.force_login(admin)
        self.client.post(reverse("toggle_social", args=[link.pk]))
        link.refresh_from_db()
        self.assertFalse(link.is_active)
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(reverse("home")), link.url)
