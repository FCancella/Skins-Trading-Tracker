import os
import requests
import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from scanner.services import buff

# Classe auxiliar para serializar objetos Decimal para JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

class Command(BaseCommand):
    help = 'Runs the pricing script for open portfolio items by interacting with the API.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base_url = "https://cstrack.online/scanner/api"
        # self.api_base_url = "http://localhost:8000/scanner/api"
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": settings.SCANNER_API_KEY
        }

    def _api_request(self, method, endpoint, data=None):
        """Função auxiliar para fazer requisições à API."""
        url = f"{self.api_base_url}/{endpoint}/"
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, data=json.dumps(data, cls=DecimalEncoder))
            else:
                raise ValueError("Unsupported HTTP method")
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"API Error at {endpoint}: {e}"))
            if e.response:
                self.stdout.write(self.style.ERROR(f"Response: {e.response.text}"))
            return None

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Starting Pricing Script (API Mode) ---'))

        # 1. OBTER LISTA DE ITENS PARA ATUALIZAR E BUSCAR PREÇOS DO BUFF
        self.stdout.write('Step 1: Getting items list to price...')
        response_data = self._api_request('GET', 'items-to-price')
        
        if not response_data:
            self.stdout.write(self.style.ERROR('Failed to get items to price. Aborting.'))
            return

        items_to_update = response_data.get("items_to_price", [])
        self.stdout.write(f'-> Found {len(items_to_update)} items needing a Buff price update.')
        
        buff_prices_payload = []
        try:
            for index, item_name in enumerate(items_to_update):
                buff_info = buff.get_item_info(item_name)
                if buff_info:
                    buff_info['name'] = item_name  # Ensure the name is included
                    self.stdout.write(f"  {index + 1}/{len(items_to_update)}: Fetched '{item_name}' - Price: {buff_info['price']}")
                    buff_prices_payload.append(buff_info)
                else:
                    self.stdout.write(self.style.WARNING(f"  {index + 1}/{len(items_to_update)}: '{item_name}' not found on Buff."))
        finally:
            if buff_prices_payload:
                self.stdout.write(self.style.SUCCESS(f'Sending {len(buff_prices_payload)} fetched Buff prices to the API...'))
                # Reutiliza o endpoint existente para salvar os preços do Buff
                response_data = self._api_request('POST', 'update-buff-prices', {"items": buff_prices_payload})
                if response_data:
                    updated_count = response_data.get("updated_items", "N/A")
                    self.stdout.write(self.style.SUCCESS(f'-> API reported {updated_count} items updated.'))

        self.stdout.write(self.style.SUCCESS('--- Pricing Script Finished ---'))