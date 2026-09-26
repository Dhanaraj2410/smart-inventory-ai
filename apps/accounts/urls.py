from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.SmartLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("password-reset/", views.SmartPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/confirm/<uidb64>/<token>/", views.SmartPasswordResetConfirmView.as_view(),
         name="password_reset_confirm"),
]
