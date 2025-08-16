from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def currency_brl(value):
    """Formata como R$ 1.234,56."""
    if value in (None, ""):
        return "—"
    try:
        val = Decimal(value)
    except Exception:
        return value
    s = f"{val:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

@register.filter
def pct(value):
    """Formata 12.34 como 12,34%."""
    if value in (None, ""):
        return "—"
    try:
        val = Decimal(value)
    except Exception:
        return value
    return f"{val:.2f}".replace(".", ",") + "%"
