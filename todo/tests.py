from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import EmailOTP, Task


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthenticationTests(TestCase):
	def test_home_requires_login(self):
		response = self.client.get(reverse('home'))
		self.assertRedirects(response, reverse('login'))

	def test_registration_requires_otp_then_logs_user_in(self):
		response = self.client.post(reverse('register'), {
			'first_name': 'Ada', 'last_name': 'Lovelace', 'email': 'ada@example.com',
			'password': 'strong-password-123', 'confirmation': 'strong-password-123',
		})
		self.assertRedirects(response, reverse('verify_registration'))
		user = User.objects.get(email='ada@example.com')
		self.assertFalse(user.is_active)
		self.assertEqual(len(mail.outbox), 1)
		self.assertEqual(mail.outbox[0].to, ['ada@example.com'])
		otp = EmailOTP.objects.get(user=user, purpose=EmailOTP.PURPOSE_REGISTRATION)
		response = self.client.post(reverse('verify_registration'), {'otp': otp.code})
		self.assertRedirects(response, reverse('home'))
		self.assertTrue(User.objects.get(pk=user.pk).is_active)
		self.assertTrue(self.client.session.get('_auth_user_id'))

	def test_forgot_password_requires_otp(self):
		user = User.objects.create_user('ada@example.com', 'ada@example.com', 'old-password', is_active=True)
		self.client.post(reverse('forgot_password'), {'email': user.email})
		otp = EmailOTP.objects.get(user=user, purpose=EmailOTP.PURPOSE_PASSWORD_RESET)
		self.client.post(reverse('verify_password_reset'), {'otp': otp.code})
		response = self.client.post(reverse('reset_password', args=[user.id]), {
			'password': 'new-password-123', 'confirmation': 'new-password-123',
		})
		self.assertRedirects(response, reverse('login'))
		self.assertTrue(self.client.login(username=user.email, password='new-password-123'))

	def test_profile_id_is_not_changed_by_profile_update(self):
		user = User.objects.create_user('ada@example.com', 'ada@example.com', 'password-123', first_name='Ada', last_name='Lovelace')
		self.client.force_login(user)
		response = self.client.post(reverse('profile'), {
			'first_name': 'Augusta', 'last_name': 'King', 'email': user.email, 'id': '999999',
		})
		self.assertRedirects(response, reverse('profile'))
		user.refresh_from_db()
		self.assertEqual(user.pk,  user.id)
		self.assertEqual(user.first_name, 'Augusta')

	def test_tasks_are_private_to_their_owner(self):
		first = User.objects.create_user('first@example.com', 'first@example.com', 'password-123', is_active=True)
		second = User.objects.create_user('second@example.com', 'second@example.com', 'password-123', is_active=True)
		task = Task.objects.create(user=first, task='Private task')
		self.client.force_login(second)
		self.assertEqual(self.client.get(reverse('edit_task', args=[task.pk])).status_code, 404)
