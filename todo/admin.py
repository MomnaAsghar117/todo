from django.contrib import admin
from .models import EmailOTP, SiteSettings, SocialLink, Task, UserProfile


class TaskAdmin(admin.ModelAdmin):
    list_display = ("task", "is_completed", "updated_at")
    search_fields = ("task",)


admin.site.register(Task, TaskAdmin)
admin.site.register(EmailOTP)
admin.site.register(UserProfile)
admin.site.register(SiteSettings)
admin.site.register(SocialLink)
