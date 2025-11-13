from django.urls import path
from . import views

urlpatterns = [
    path('manage/', views.manage_store, name='manage_store'),
    path('<str:username>/', views.public_store, name='public_store'),
]