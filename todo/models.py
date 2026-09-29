from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    task = models.CharField(max_length=250)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # this is a string representation of the model, it will return the task name when we print the object
    def __str__(self):
        return self.task


class EmailOTP(models.Model):
    PURPOSE_REGISTRATION = 'registration'
    PURPOSE_PASSWORD_RESET = 'password_reset'
    PURPOSE_CHOICES = (
        (PURPOSE_REGISTRATION, 'Registration'),
        (PURPOSE_PASSWORD_RESET, 'Password reset'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_otps')
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        return timezone.now() <= self.created_at + timezone.timedelta(minutes=10)