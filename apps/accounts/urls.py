from django.urls import path
from apps.accounts import views

urlpatterns = [
    path("register/", views.RegisterCompleteView.as_view(), name="register"),
    path(
        "register/otp/",
        views.RegisterRequestOtpView.as_view(),
        name="register-request-otp",
    ),
]
