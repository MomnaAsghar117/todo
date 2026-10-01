from PIL import Image
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

MAX_UPLOAD_SIZE = 5 * 1024 * 1024


def validate_hex_color(value):
    if (
        not isinstance(value, str)
        or len(value) != 7
        or value[0] != "#"
        or any(character not in "0123456789abcdefABCDEF" for character in value[1:])
    ):
        raise ValidationError("Choose a valid color.")


def validate_image_upload(upload):
    if upload.size > MAX_UPLOAD_SIZE:
        raise ValidationError("Images must be 5 MB or smaller.")
    try:
        image = Image.open(upload)
        image.verify()
    except (Image.UnidentifiedImageError, OSError):
        raise ValidationError("Upload a valid image file.")
    finally:
        upload.seek(0)


class UserProfile(models.Model):
    BACKGROUND_CHOICES = (
        ("#ffffff", "White"),
        ("#f6efe3", "Cream"),
        ("#e7d6c5", "Beige"),
        ("#8b5e3c", "Brown"),
        ("#3f2d24", "Dark Brown"),
        ("#eef1f3", "Light Gray"),
        ("#dcecf7", "Blue"),
        ("#dcefe1", "Green"),
        ("#ebe3f7", "Lavender"),
        ("#f8dfe6", "Pink"),
    )
    ACCENT_CHOICES = (
        ("#8b5e3c", "Brown"),
        ("#1f2522", "Black"),
        ("#2774ae", "Blue"),
        ("#367a56", "Green"),
        ("#7654a3", "Purple"),
        ("#c24d70", "Pink"),
        ("#d46b32", "Orange"),
        ("#287f7c", "Teal"),
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile_settings"
    )
    profile_picture = models.ImageField(
        upload_to="profile_pictures/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_image_upload],
    )
    background_image = models.ImageField(
        upload_to="backgrounds/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_image_upload],
    )
    background_color = models.CharField(
        max_length=7, default="#f6efe3", validators=[validate_hex_color]
    )
    accent_color = models.CharField(
        max_length=7, default="#8b5e3c", validators=[validate_hex_color]
    )
    surface_color = models.CharField(
        max_length=7, default="#ffffff", validators=[validate_hex_color]
    )
    default_task_color = models.CharField(
        max_length=7, default="#d46b32", validators=[validate_hex_color]
    )
    default_priority = models.CharField(max_length=10, default="medium")
    categories_seeded = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} settings"

    @property
    def accent_text_color(self):
        red = int(self.accent_color[1:3], 16)
        green = int(self.accent_color[3:5], 16)
        blue = int(self.accent_color[5:7], 16)
        return (
            "#201c18"
            if (red * 299 + green * 587 + blue * 114) / 1000 > 150
            else "#ffffff"
        )

    @property
    def background_text_color(self):
        red = int(self.background_color[1:3], 16)
        green = int(self.background_color[3:5], 16)
        blue = int(self.background_color[5:7], 16)
        return (
            "#201c18"
            if (red * 299 + green * 587 + blue * 114) / 1000 > 150
            else "#ffffff"
        )

    @property
    def surface_text_color(self):
        red = int(self.surface_color[1:3], 16)
        green = int(self.surface_color[3:5], 16)
        blue = int(self.surface_color[5:7], 16)
        return (
            "#201c18"
            if (red * 299 + green * 587 + blue * 114) / 1000 > 150
            else "#ffffff"
        )


class Task(models.Model):
    PRIORITY_CHOICES = (("high", "High"), ("medium", "Medium"), ("low", "Low"))
    CATEGORY_CHOICES = (
        ("study", "Study"),
        ("work", "Work"),
        ("personal", "Personal"),
        ("shopping", "Shopping"),
        ("health", "Health"),
        ("other", "Other"),
    )
    COLOR_CHOICES = (
        ("#d94c4c", "Red"),
        ("#df7b32", "Orange"),
        ("#d6aa2b", "Yellow"),
        ("#4a9a62", "Green"),
        ("#4285b5", "Blue"),
        ("#7654a3", "Purple"),
        ("#c24d70", "Pink"),
        ("#8b5e3c", "Brown"),
        ("#87939b", "Gray"),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="tasks"
    )
    task = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    category = models.CharField(max_length=50, blank=True)
    due_date = models.DateField(blank=True, null=True)
    color = models.CharField(
        max_length=7, default="#d46b32", validators=[validate_hex_color]
    )
    is_favorite = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # this is a string representation of the model, it will return the task name when we print the object
    def __str__(self):
        return self.task

    @property
    def is_overdue(self):
        return bool(
            self.due_date
            and not self.is_completed
            and self.due_date < timezone.localdate()
        )

    @property
    def due_label(self):
        if not self.due_date:
            return "No due date"
        delta = (self.due_date - timezone.localdate()).days
        if delta < 0 and not self.is_completed:
            return "Overdue"
        if delta == 0:
            return "Due today"
        if delta == 1:
            return "Due tomorrow"
        return f"Due {self.due_date:%b} {self.due_date.day}, {self.due_date.year}"

    @property
    def text_color(self):
        red = int(self.color[1:3], 16)
        green = int(self.color[3:5], 16)
        blue = int(self.color[5:7], 16)
        return (
            "#201c18"
            if (red * 299 + green * 587 + blue * 114) / 1000 > 150
            else "#ffffff"
        )


class Category(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="task_categories"
    )
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_category_per_user"
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class SiteSettings(models.Model):
    website_name = models.CharField(max_length=120, default="Daymark")
    homepage_quote = models.CharField(
        max_length=255, default="Keep the important things moving."
    )
    footer_description = models.CharField(
        max_length=255, default="Make room for the things that matter."
    )
    contact_email = models.EmailField(blank=True)

    def __str__(self):
        return self.website_name


class SocialLink(models.Model):
    PLATFORM_CHOICES = (
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("twitter", "Twitter/X"),
        ("linkedin", "LinkedIn"),
        ("youtube", "YouTube"),
        ("tiktok", "TikTok"),
        ("other", "Other"),
    )

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "platform"]

    def __str__(self):
        return self.get_platform_display()


class EmailOTP(models.Model):
    PURPOSE_REGISTRATION = "registration"
    PURPOSE_PASSWORD_RESET = "password_reset"
    PURPOSE_CHOICES = (
        (PURPOSE_REGISTRATION, "Registration"),
        (PURPOSE_PASSWORD_RESET, "Password reset"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        return timezone.now() <= self.created_at + timezone.timedelta(minutes=10)
