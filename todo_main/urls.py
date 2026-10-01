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
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='landing'),
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('verify-registration/', views.verify_registration, name='verify_registration'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-password-reset/', views.verify_password_reset, name='verify_password_reset'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    path('profile/', views.profile, name='profile'),
    path('profile/password/', views.change_password, name='change_password'),
    
    # ToDo
    path('todo/',  include('todo.urls')),
    
]
