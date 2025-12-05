from django.urls import path
from rest_framework_simplejwt import views as jwt_views

from authentication.views import auth_views

app_name = "auth"

urlpatterns = [
    # User Registration
    path(
        "register",
        auth_views.UserRegistrationView.as_view(),
        name="user-register",
    ),
    # User Login
    path(
        "login",
        auth_views.LoginView.as_view(),
        name="login",
    ),
    # Refresh Token
    path(
        "token/refresh",
        jwt_views.TokenRefreshView.as_view(),
        name="token-refresh",
    ),
]
