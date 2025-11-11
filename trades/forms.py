"""
Form definitions for the `trades` app.

Two model forms are provided:

* ``AddTradeForm`` for creating new trade entries, requiring an item name,
  buy price and buy source.
* ``SellTradeForm`` for updating existing trades with sell information
  (sell price, sell source, and buy date). When updating an unsold item,
  only these fields are editable.

These forms leverage Django's ModelForm capabilities to automatically
generate fields based on the ``Trade`` model and perform built‑in
validation. Choice fields are rendered as select controls in templates.
"""
from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Trade, Investment, SOURCE_CHOICES

CURRENCY_CHOICES = [
    ('BRL', 'BRL'),
    ('CNY', 'CNY'),
    ('USD', 'USD'),
]

class EditTradeForm(forms.ModelForm):
    """
    Form for creating or updating a trade.
    Responsável pela ação do Update dentro do padrão CRUD.
    """

    buy_price_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial='BRL', widget=forms.RadioSelect, required=False)
    sell_price_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial='BRL', widget=forms.RadioSelect, required=False)

    class Meta:
        model = Trade
        fields = [
            'item_name', 'buy_price', 'buy_source', 'buy_date',
            'sell_price', 'sell_source', 'sell_date'
        ]
        widgets = {
            'buy_date': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'sell_date': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')
            if name in ['buy_price', 'sell_price']:
                field.widget.attrs['class'] += ' price-input'
                field.widget.attrs['inputmode'] = 'numeric'

    def save(self, commit=True, owner=None):
        obj = super().save(commit=False)
        # Owner is required only when creating a new object
        if owner and not obj.pk:
            obj.owner = owner
        elif not obj.owner:
             raise ValueError("TradeForm needs an owner to be saved.")
        
        if commit:
            obj.save()
        return obj


class SellTradeForm(forms.ModelForm):
    """
    Form for updating a trade with sell details.
    Responsável pela ação do Update dentro do padrão CRUD.
    """

    sell_price_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial='BRL', widget=forms.RadioSelect)

    class Meta:
        model = Trade
        fields = ['sell_price', 'sell_source', 'sell_date']
        widgets = {
            'sell_date': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Prefill the sell_date with today if it doesn't exist
        if not self.instance.sell_date:
            self.initial.setdefault('sell_date', timezone.now())
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')
            if name == 'sell_price':
                field.widget.attrs['class'] += ' price-input'
                field.widget.attrs['inputmode'] = 'numeric'

class InvestmentForm(forms.ModelForm):
    """Form for creating a new investment."""

    class Meta:
        model = Investment
        fields = ['amount', 'description', 'source', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')
            if name == 'amount':
                field.widget.attrs['class'] += ' price-input'
                field.widget.attrs['inputmode'] = 'numeric'

    def save(self, commit=True, owner=None):
        obj = super().save(commit=False)
        if owner and not obj.pk:
            obj.owner = owner
        elif not obj.owner:
            raise ValueError("InvestmentForm needs an owner to be saved.")
        
        if commit:
            obj.save()
        return obj

class AddTradeForm(forms.Form):
    """
    Form for adding multiple trades at once.
    Responsável pela ação do Create dentro do padrão CRUD.
    """
    item_name = forms.CharField(max_length=100)
    quantity = forms.IntegerField(min_value=1, initial=1)
    buy_price = forms.DecimalField(max_digits=10, decimal_places=2)
    buy_source = forms.ChoiceField(choices=SOURCE_CHOICES)
    buy_date = forms.DateTimeField(widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}), initial=timezone.now)
    buy_price_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial='BRL', widget=forms.RadioSelect(attrs={'class': 'btn-check'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply default bootstrap classes to fields
        for name, field in self.fields.items():
            if name == 'buy_price_currency': continue
            css_class = 'form-select' if isinstance(field, forms.ChoiceField) else 'form-control'
            field.widget.attrs.setdefault('class', css_class)
            if name == 'buy_price':
                field.widget.attrs['class'] += ' price-input'
                field.widget.attrs['inputmode'] = 'numeric'

class UsernameChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        help_texts = {
            'username': 'Obrigatório. 150 caracteres ou menos. Letras, dígitos e @/./+/-/_ apenas.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})

    def clean_username(self):
        username = self.cleaned_data['username']
        # Verifica se outro usuário (excluindo o usuário atual) já tem esse nome
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este nome de usuário já está em uso.")
        return username