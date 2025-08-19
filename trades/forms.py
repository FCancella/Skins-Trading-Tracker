"""
Form definitions for the `trades` app.

Two model forms are provided:

* ``TradeForm`` for creating new trade entries, requiring an item name,
  buy price and buy source.
* ``SellTradeForm`` for updating existing trades with sell information
  (sell price, sell source, and date sold). When updating an unsold item,
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
    """Form for creating a new trade."""

    class Meta:
        model = Trade
        fields = ['item_name', 'buy_price', 'buy_source', 'date_of_purchase']
        widgets = {
            'date_of_purchase': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
    
    def save(self, commit=True, owner=None):
        obj = super().save(commit=False)
        if owner is None:
            # fail fast to avoid orphan trades
            raise ValueError("TradeForm.save(owner=...) is required to set Trade.owner")
        obj.owner = owner
        if commit:
            obj.save()
        return obj


class SellTradeForm(forms.ModelForm):
    """Form for updating a trade with sell details."""

    class Meta:
        model = Trade
        fields = ['sell_price', 'sell_source', 'date_sold']
        widgets = {
            'date_sold': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Prefill the date_sold with today if it doesn't exist
        if not self.instance.date_sold:
            self.initial.setdefault('date_sold', timezone.now().date())
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