from .models import SiteSettings, SocialLink, UserProfile


def personalization(request):
    site_settings, _ = SiteSettings.objects.get_or_create(pk=1)
    active_social_links = SocialLink.objects.filter(is_active=True)
    if not request.user.is_authenticated:
        return {
            "site_settings": site_settings,
            "active_social_links": active_social_links,
        }
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return {
        "profile": profile,
        "site_settings": site_settings,
        "active_social_links": active_social_links,
    }
