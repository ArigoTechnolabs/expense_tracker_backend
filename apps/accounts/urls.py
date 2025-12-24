from django.urls import path
from apps.accounts import views

urlpatterns = [
    path("register/", views.RegisterCompleteView.as_view(), name="register"),
    path(
        "register/otp/",
        views.RegisterRequestOtpView.as_view(),
        name="register-request-otp",
    ),
    path("login/", views.MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("forgot-password/request-otp/", views.ForgotPasswordRequestOtpView.as_view()),
    path("forgot-password/reset/", views.ResetPasswordView.as_view()),
]
