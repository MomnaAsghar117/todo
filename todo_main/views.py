import random

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from todo.models import EmailOTP, Task

User = get_user_model()


def _send_otp(user, purpose):
    code = f'{random.randint(0, 999999):06d}'
    EmailOTP.objects.filter(user=user, purpose=purpose).delete()
    EmailOTP.objects.create(user=user, purpose=purpose, code=code)
    send_mail(
        'Your ToDo App verification code',
        f'Your verification code is {code}. It expires in 10 minutes.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def _valid_otp(user, purpose, code):
    otp = EmailOTP.objects.filter(user=user, purpose=purpose).order_by('-created_at').first()
    return otp and otp.is_valid and otp.code == code

def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tasks = Task.objects.filter(user=request.user, is_completed=False).order_by('-updated_at')
    completed_tasks = Task.objects.filter(user=request.user, is_completed=True)
    context = {
        "tasks": tasks,
        "completed_tasks": completed_tasks,
    }
    return render(request, "home.html", context)


@never_cache
def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirmation = request.POST.get('confirmation', '')
        if not email or not password or password != confirmation:
            messages.error(request, 'Enter all fields and make sure both passwords match.')
        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'An account with this email already exists.')
        else:
            user = User(username=email, email=email, first_name=request.POST.get('first_name', '').strip(), last_name=request.POST.get('last_name', '').strip(), is_active=False)
            user.set_password(password)
            user.save()
            _send_otp(user, EmailOTP.PURPOSE_REGISTRATION)
            request.session['registration_user_id'] = user.id
            return redirect('verify_registration')
    return render(request, 'register.html')


@never_cache
def verify_registration(request):
    user = User.objects.filter(id=request.session.get('registration_user_id'), is_active=False).first()
    if not user:
        return redirect('register')
    if request.method == 'POST':
        if _valid_otp(user, EmailOTP.PURPOSE_REGISTRATION, request.POST.get('otp', '').strip()):
            user.is_active = True
            user.save(update_fields=['is_active'])
            EmailOTP.objects.filter(user=user, purpose=EmailOTP.PURPOSE_REGISTRATION).delete()
            request.session.pop('registration_user_id', None)
            login(request, user)
            return redirect('home')
        messages.error(request, 'That code is invalid or expired.')
    return render(request, 'verify_otp.html', {'title': 'Verify your email', 'description': 'Enter the 6-digit code sent to your email.'})


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('email', '').strip().lower(), password=request.POST.get('password', ''))
        if user:
            login(request, user)
            return redirect('home')
        messages.error(request, 'Invalid email or password, or your email is not verified.')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@never_cache
def forgot_password(request):
    if request.method == 'POST':
        user = User.objects.filter(email__iexact=request.POST.get('email', '').strip().lower(), is_active=True).first()
        if user:
            _send_otp(user, EmailOTP.PURPOSE_PASSWORD_RESET)
            request.session['password_reset_user_id'] = user.id
            return redirect('verify_password_reset')
        messages.error(request, 'No verified account was found for that email.')
    return render(request, 'forgot_password.html')


@never_cache
def verify_password_reset(request):
    user = User.objects.filter(id=request.session.get('password_reset_user_id'), is_active=True).first()
    if not user:
        return redirect('forgot_password')
    if request.method == 'POST':
        if _valid_otp(user, EmailOTP.PURPOSE_PASSWORD_RESET, request.POST.get('otp', '').strip()):
            EmailOTP.objects.filter(user=user, purpose=EmailOTP.PURPOSE_PASSWORD_RESET).delete()
            return redirect('reset_password', user_id=user.id)
        messages.error(request, 'That code is invalid or expired.')
    return render(request, 'verify_otp.html', {'title': 'Verify password reset', 'description': 'Enter the 6-digit code sent to your email.'})


@never_cache
def reset_password(request, user_id):
    if request.session.get('password_reset_user_id') != user_id:
        return redirect('forgot_password')
    user = get_object_or_404(User, id=user_id, is_active=True)
    if request.method == 'POST':
        password = request.POST.get('password', '')
        if password and password == request.POST.get('confirmation', ''):
            user.set_password(password)
            user.save(update_fields=['password'])
            request.session.pop('password_reset_user_id', None)
            messages.success(request, 'Your password has been reset. You can now log in.')
            return redirect('login')
        messages.error(request, 'Enter matching, non-empty passwords.')
    return render(request, 'reset_password.html', {'title': 'Create a new password'})


@login_required
@never_cache
def profile(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exclude(id=request.user.id).exists():
            messages.error(request, 'That email is already in use.')
        elif email:
            request.user.first_name = request.POST.get('first_name', '').strip()
            request.user.last_name = request.POST.get('last_name', '').strip()
            request.user.email = email
            request.user.username = email
            request.user.save(update_fields=['first_name', 'last_name', 'email', 'username'])
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    return render(request, 'profile.html')


@login_required
@never_cache
def change_password(request):
    if request.method == 'POST':
        password = request.POST.get('password', '')
        if password and password == request.POST.get('confirmation', ''):
            request.user.set_password(password)
            request.user.save(update_fields=['password'])
            login(request, request.user)
            messages.success(request, 'Password updated.')
            return redirect('profile')
        messages.error(request, 'Enter matching, non-empty passwords.')
    return render(request, 'reset_password.html', {'title': 'Change your password', 'authenticated_reset': True})