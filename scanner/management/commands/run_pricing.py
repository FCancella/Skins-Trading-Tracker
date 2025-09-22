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
        
        # Lista para guardar as linhas do log
        log_summary_lines = []
        
        # --- 1. OBTER LISTA DE ITENS E BUSCAR PREÇOS ---
        self.stdout.write('Step 1: Getting items list to price...')
        response_data = self._api_request('GET', 'items-to-price')
        
        if not response_data:
            error_message = 'Failed to get items to price from API. Aborting.'
            self.stdout.write(self.style.ERROR(error_message))
            log_summary_lines.append(error_message)
            self._send_log_to_api("\n".join(log_summary_lines))
            return

        items_to_update = response_data.get("items_to_price", [])
        found_items_message = f'Found {len(items_to_update)} items needing a Buff price update.'
        self.stdout.write(f'-> {found_items_message}')
        log_summary_lines.append(found_items_message)
        
        buff_prices_payload = []
        items_not_found = 0
        try:
            for index, item_name in enumerate(items_to_update):
                buff_info = buff.get_item_info(item_name)
                if buff_info:
                    buff_info['name'] = item_name
                    self.stdout.write(f"  {index + 1}/{len(items_to_update)}: Fetched '{item_name}' - Price: {buff_info['price']}")
                    if abs(buff_info['price']-buff_info['price']) < 0.01:
                        continue
                    buff_prices_payload.append(buff_info)
                else:
                    items_not_found += 1
                    self.stdout.write(self.style.WARNING(f"  {index + 1}/{len(items_to_update)}: '{item_name}' not found on Buff."))
        
        finally:
            # Adiciona estatísticas sobre a busca de preços ao log
            log_summary_lines.append(f"Successfully fetched prices for {len(buff_prices_payload)} items.")
            if items_not_found > 0:
                log_summary_lines.append(f"Could not find {items_not_found} items on Buff.")

            # --- 2. ENVIAR PREÇOS ATUALIZADOS PARA A API ---
            if buff_prices_payload:
                self.stdout.write(self.style.SUCCESS(f'Sending {len(buff_prices_payload)} fetched Buff prices to the API...'))
                response_data = self._api_request('POST', 'update-buff-prices', {"items": buff_prices_payload})
                if response_data:
                    updated_count = response_data.get("updated_items", 0)
                    success_message = f'API reported {updated_count} items updated successfully.'
                    self.stdout.write(self.style.SUCCESS(f'-> {success_message}'))
                    log_summary_lines.append(success_message)
                else:
                    error_message = 'API call to update-buff-prices failed or returned no data.'
                    self.stdout.write(self.style.ERROR(error_message))
                    log_summary_lines.append(error_message)

        # --- 3. ENVIAR O RESUMO FINAL PARA A API DE LOGS ---
        final_log_message = "\n".join(log_summary_lines)
        self._send_log_to_api(final_log_message)
        
        self.stdout.write(self.style.SUCCESS('--- Pricing Script Finished ---'))

    def _send_log_to_api(self, message):
        """Função auxiliar para enviar a mensagem de log para a API."""
        self.stdout.write("\nSending final summary to log API...")
        self._api_request('POST', 'logs', {"message": message})
        self.stdout.write("-> Log sent.")
