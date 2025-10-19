from decimal import Decimal
import requests
from django.core.cache import cache

def _get_exchange_rate(currency: str) -> Decimal | None:
    '''Obtém a taxa de câmbio atual para a moeda especificada em relação ao BRL (moeda exibida).'''
    rate = cache.get(currency)
    if rate:
        return rate
    try:
        response = requests.get(f"https://open.er-api.com/v6/latest/{currency}")
        response.raise_for_status()
        data = response.json()
        rate = Decimal(data["rates"]["BRL"]).quantize(Decimal("0.0001"))
        cache.set(currency, rate)
        return rate
    except (requests.RequestException, KeyError, TypeError):
        return None