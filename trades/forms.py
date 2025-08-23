"""
Form definitions for the `trades` app.

Two model forms are provided:

* ``TradeForm`` for creating new trade entries, requiring an item name,
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
from django.utils import timezone

from .models import Trade, Investment

class TradeForm(forms.ModelForm):
    """Form for creating or updating a trade."""

    class Meta:
        model = Trade
        fields = [
            'item_name', 'buy_price', 'buy_source', 'buy_date',
            'sell_price', 'sell_source', 'sell_date'
        ]
        widgets = {
            'buy_date': forms.DateInput(attrs={'type': 'date'}),
            'sell_date': forms.DateInput(attrs={'type': 'date'}),
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
    """Form for updating a trade with sell details."""

    class Meta:
        model = Trade
        fields = ['sell_price', 'sell_source', 'sell_date']
        widgets = {
            'sell_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Prefill the sell_date with today if it doesn't exist
        if not self.instance.sell_date:
            self.initial.setdefault('sell_date', timezone.now().date())
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

class InvestmentForm(forms.ModelForm):
    """Form for creating a new investment."""

    class Meta:
        model = Investment
        fields = ['amount', 'description', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def save(self, commit=True, owner=None):
        obj = super().save(commit=False)
        if owner is None:
            raise ValueError("InvestmentForm.save(owner=...) is required to set Investment.owner")
        obj.owner = owner
        if commit:
            obj.save()
        return obj