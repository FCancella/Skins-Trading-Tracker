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

class CustomUserCreationForm(UserCreationForm):
    """
    Um formulário de criação de utilizador que inclui o campo de email.
    """
    email = forms.EmailField(
        required=True,
        help_text='Necessary for password recovery.'
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_email(self):
        """Valida se o email já está em uso."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este endereço de email já está a ser utilizado.")
        return email

class EditTradeForm(forms.ModelForm):
    buy_price_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial='BRL', widget=forms.RadioSelect, required=False)
    sell_price_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial='BRL', widget=forms.RadioSelect, required=False)

    """Form for creating or updating a trade."""

    class Meta:
        model = Trade
        fields = [
            'item_name', 'buy_price', 'buy_source', 'buy_date',
            'sell_price', 'sell_source', 'sell_date'
        ]
        widgets = {
            'buy_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'sell_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

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
    sell_price_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial='BRL', widget=forms.RadioSelect)

    """Form for updating a trade with sell details."""

    class Meta:
        model = Trade
        fields = ['sell_price', 'sell_source', 'sell_date']
        widgets = {
            'sell_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Prefill the sell_date with today if it doesn't exist
        if not self.instance.sell_date:
            self.initial.setdefault('sell_date', timezone.now())
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

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
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

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
    """Form for adding multiple trades at once."""
    item_name = forms.CharField(max_length=100)
    quantity = forms.IntegerField(min_value=1, initial=1)
    buy_price = forms.DecimalField(max_digits=10, decimal_places=2)
    buy_source = forms.ChoiceField(choices=SOURCE_CHOICES)
    buy_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}), initial=timezone.now)
    buy_price_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial='BRL', widget=forms.RadioSelect(attrs={'class': 'btn-check'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply default bootstrap classes to fields
        for name, field in self.fields.items():
            if name == 'buy_price_currency': continue
            css_class = 'form-select' if isinstance(field, forms.ChoiceField) else 'form-control'
            field.widget.attrs.setdefault('class', css_class)