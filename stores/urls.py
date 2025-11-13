from django.urls import path
from . import views

urlpatterns = [
    path('manage/', views.manage_store, name='manage_store'),
    path('log-checkout/', views.log_cart_checkout, name='log_cart_checkout'),
    path('<str:username>/', views.public_store, name='public_store'),
]