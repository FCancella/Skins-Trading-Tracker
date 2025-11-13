from django import forms
from .models import Store

class StoreSettingsForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'steam_id', 'fee_percentage', 'whatsapp']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white', 'placeholder': 'Ex: Loja do Pedro'}),
            'steam_id': forms.TextInput(attrs={'class': 'form-control bg-dark text-white'}),
            'fee_percentage': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control bg-dark text-white', 'placeholder': 'Ex: 5521999999999'}),
        }
        labels = {
            'name': 'Nome da Loja',
            'steam_id': 'Steam ID64',
            'fee_percentage': 'Taxa de Venda (%)',
            'whatsapp': 'WhatsApp (com DDD)',
        }