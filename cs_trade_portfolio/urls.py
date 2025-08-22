"""
URL configuration for the Counter‑Strike skin trade management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from __future__ import annotations

from trades import views as trade_views
from django.urls import include, path
from django.contrib import admin

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),  # login, logout, password views
 
    path("", trade_views.home, name="home"),
    path("portfolio/", trade_views.index, name="index"),
    path("spectator/", trade_views.spectator, name="spectator"),
    path("signup/", trade_views.signup, name="signup"),
    path("profile/toggle/", trade_views.toggle_profile_public, name="toggle_profile_public"),
]