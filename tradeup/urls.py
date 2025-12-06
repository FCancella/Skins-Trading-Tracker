from django.urls import path
from . import views

app_name = 'tradeup'

urlpatterns = [
    path('', views.tradeup_calculator, name='calculator'),
    path('search/', views.search_items, name='search_items'), # Nova rota da API
]