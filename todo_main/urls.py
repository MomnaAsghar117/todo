"""
URL configuration for todo_main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from . import views
from todo import views as todo_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.login_view, name="landing"),
    path("home/", todo_views.home, name="home"),
    path("admin-dashboard/", todo_views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/users/", todo_views.admin_users, name="admin_users"),
    path("admin-dashboard/settings/", todo_views.admin_settings, name="admin_settings"),
    path("admin-dashboard/customization/", todo_views.admin_customization, name="admin_customization"),
    path("admin-dashboard/social/", todo_views.admin_social, name="admin_social"),
    path("admin-dashboard/social/<int:pk>/delete/", todo_views.delete_social, name="delete_social"),
    path("admin-dashboard/social/<int:pk>/toggle/", todo_views.toggle_social, name="toggle_social"),
    path("admin-dashboard/website/", todo_views.view_website, name="view_website"),
    path("register/", views.register, name="register"),
    path("verify-registration/", views.verify_registration, name="verify_registration"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path(
        "verify-password-reset/",
        views.verify_password_reset,
        name="verify_password_reset",
    ),
    path("reset-password/<int:user_id>/", views.reset_password, name="reset_password"),
    path("profile/", todo_views.profile_settings, name="profile"),
    path("profile/password/", views.change_password, name="change_password"),
    # ToDo
    path("todo/", include("todo.urls")),
]
