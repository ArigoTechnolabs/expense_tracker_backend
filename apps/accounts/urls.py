from django.urls import path
from apps.accounts.views import (
    MyTokenObtainPairView,
    RegisterEmailView,
    ResendOtpView,
    VerifyOtpView,
)

urlpatterns = [
    path("register/", RegisterEmailView.as_view(), name="register-email"),
    path("verify-otp/", VerifyOtpView.as_view(), name="verify-otp"),
    path("resend-otp/", ResendOtpView.as_view(), name="resend-otp"),
    path("login/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
]
