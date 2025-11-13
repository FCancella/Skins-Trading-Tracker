from django import forms
from .models import Store, StoreItem

class StoreSettingsForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['steam_id', 'fee_percentage', 'whatsapp']
        widgets = {
            'steam_id': forms.TextInput(attrs={'class': 'form-control bg-dark text-white'}),
            'fee_percentage': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control bg-dark text-white', 'placeholder': 'Ex: 5521999999999'}),
        }
        labels = {
            'steam_id': 'Steam ID64',
            'fee_percentage': 'Taxa de Venda (%)',
            'whatsapp': 'WhatsApp (com DDD)',
        }