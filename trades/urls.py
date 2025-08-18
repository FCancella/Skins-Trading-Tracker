from django.contrib import admin
from django.urls import path, include
from trades import views as trade_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", trade_views.index, name="index"),
    path("accounts/", include("django.contrib.auth.urls")),  # login, logout, password views
    path("signup/", trade_views.signup, name="signup"),
]
