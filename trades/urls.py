"""
URL configuration for the `trades` app.

Currently, all views are served from the root path. Both adding new trades
and updating existing trades submit forms to this endpoint. The view
dispatches appropriately based on POST parameters.
"""
from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
]