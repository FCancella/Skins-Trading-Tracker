from django import forms
from .models import Store

class StoreSettingsForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'color', 'steam_id', 'fee_percentage', 'whatsapp']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control bg-dark text-white', 'placeholder': 'Ex: Loja do Pedro'}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color w-100 bg-dark border-secondary', 'type': 'color', 'title': 'Escolha a cor da sua loja'}),
            'steam_id': forms.TextInput(attrs={'class': 'form-control bg-dark text-white'}),
            'fee_percentage': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control bg-dark text-white', 'placeholder': 'Ex: 5521999999999'}),
        }
        labels = {
            'name': 'Nome da Loja',
            'color': 'Cor do Tema',
            'steam_id': 'Steam ID64',
            'fee_percentage': 'Taxa de Venda (%)',
            'whatsapp': 'WhatsApp (com DDD)',
        }