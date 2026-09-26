from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Inventory Manager"
        VIEWER = "VIEWER", "Viewer"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_manager_role(self):
        return self.role in (self.Role.ADMIN, self.Role.MANAGER) or self.is_superuser

    def can_manage_inventory(self):
        return self.is_manager_role

    def can_train_models(self):
        return self.is_admin_role

    def can_manage_users(self):
        return self.is_admin_role

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
