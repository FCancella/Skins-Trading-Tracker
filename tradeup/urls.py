from django.urls import path
from . import views

app_name = 'tradeup'

urlpatterns = [
    path('calculator/', views.tradeup_calculator, name='calculator'),
    path('search/', views.search_items, name='search_items'),
    path('calculate/', views.calculate_contract_api, name='calculate_contract'),
    path('random/', views.random_item, name='random_item'),
]