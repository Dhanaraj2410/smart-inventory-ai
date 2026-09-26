"""
Reusable role-based access helpers.

Roles:
    ADMIN   - full access: manage users, upload datasets, train models, AI config
    MANAGER - manage inventory, view predictions/recommendations, run simulations, use AI
    VIEWER  - read-only dashboards, product analytics, predictions
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


def role_required(*roles):
    """View decorator: raise PermissionDenied unless request.user.role in roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise PermissionDenied("Login required.")
            if user.is_superuser or user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You do not have permission to perform this action.")
        return _wrapped
    return decorator


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.is_admin_role))


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.is_manager_role))


class ReadOnlyOrManager(BasePermission):
    """Viewers get read-only (GET/HEAD/OPTIONS); managers/admins get full access."""
    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if request.method in self.SAFE_METHODS:
            return True
        return u.is_superuser or u.is_manager_role
