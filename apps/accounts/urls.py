from django.urls import path
from apps.accounts.views import RegisterEmailView

urlpatterns = [
    path("register/", RegisterEmailView.as_view(), name="register-email"),
    # path("verify-otp/", OtpVerifyView.as_view(), name="verify-otp"),
]
