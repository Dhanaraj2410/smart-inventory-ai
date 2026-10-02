"""Authentication and permission tests."""
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User


class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_registration_creates_user_with_default_role(self):
        resp = self.client.post(reverse("accounts:register"), {
            "username": "newuser", "email": "new@example.com",
            "first_name": "New", "last_name": "User", "role": User.Role.ADMIN,
            "password1": "SuperSecret123!", "password2": "SuperSecret123!",
        })
        self.assertTrue(User.objects.filter(username="newuser").exists())
        user = User.objects.get(username="newuser")
        self.assertEqual(user.role, User.Role.VIEWER)

    def test_login_success(self):
        User.objects.create_user(username="loginuser", password="pass12345")
        resp = self.client.post(reverse("accounts:login"), {"username": "loginuser", "password": "pass12345"})
        self.assertEqual(resp.status_code, 302)

    def test_login_failure(self):
        resp = self.client.post(reverse("accounts:login"), {"username": "nouser", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid username or password")

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard:home"))
        self.assertEqual(resp.status_code, 302)

    def test_logout_requires_post(self):
        user = User.objects.create_user(username="logoutuser", password="pass12345")
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:logout"))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_post_ends_session(self):
        user = User.objects.create_user(username="logoutuser", password="pass12345")
        self.client.force_login(user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("accounts:login"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_manager_role_permission(self):
        from apps.accounts.models import User as U
        admin = U.objects.create_user(username="a1", password="p1", role=U.Role.ADMIN)
        viewer = U.objects.create_user(username="v1", password="p1", role=U.Role.VIEWER)
        self.assertTrue(admin.can_manage_inventory())
        self.assertFalse(viewer.can_manage_inventory())
        self.assertTrue(admin.can_train_models())
        self.assertFalse(viewer.can_train_models())
