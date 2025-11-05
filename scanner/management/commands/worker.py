import requests
import time
import json
from random import uniform, randint
import sys

# --- CONFIGURAÇÃO ---
# Altere para a URL do seu servidor e sua API Key
API_BASE_URL = "https://cstrack.online"
# API_BASE_URL = "http://127.0.0.1:8000"
API_KEY = "APIKEY"
# --------------------

# Headers para a API do seu servidor
API_HEADERS = {
    "Content-Type": "application/json",
    "X-API-KEY": API_KEY
}

# Headers para a API do Buff
BUFF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.1 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://buff.163.com/",
    "Origin": "https://buff.163.com"
}
# (Se precisar de cookies, adicione-os aqui)
# BUFF_COOKIES = {...}

def get_work_batch():
    """Busca um lote de trabalho do servidor Django."""
    url = f"{API_BASE_URL}/scanner/api/get-item-batch/"
    print("Buscando novo lote de trabalho...")
    try:
        response = requests.get(url, headers=API_HEADERS, timeout=15)
        response.raise_for_status()
        return response.json() # Retorna o JSON completo (incluindo a taxa)
    except requests.RequestException as e:
        print(f"Erro ao buscar lote de trabalho: {e}")
        return None

def call_buff_api(buff_item_id: int):
    """
    Chama a API do Buff para um ID de item específico.
    Retorna o preço em CNY e a contagem de ofertas.
    """
    if not buff_item_id:
        return None
        
    buff_api_url = f"https://buff.163.com/api/market/goods/sell_order?game=csgo&page_num=1&goods_id={buff_item_id}"
    
    errors = 0
    while errors < 3:
        try:
            response = requests.get(buff_api_url, headers=BUFF_HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            items_list = data.get("data", {}).get("items", [])
            offers_count = data.get("data", {}).get("total_count", 0)

            if items_list:
                price_cny = items_list[0].get("price")
                return {"price_cny": float(price_cny), "offers": int(offers_count)}

        except Exception as e:
            errors += 1
            print(f"  > Erro na API do Buff (ID: {buff_item_id}): {e}")
            time.sleep(5)
    return None

def submit_work_batch(prices_payload, cny_brl_rate):
    """Envia o lote de preços (em CNY) para o servidor Django."""
    if not prices_payload:
        return
        
    url = f"{API_BASE_URL}/scanner/api/submit-item-batch/"
    payload = json.dumps({
        "prices": prices_payload,
        "cny_brl_rate": str(cny_brl_rate) # Envia a taxa de volta para consistência
    })
    
    try:
        response = requests.post(url, data=payload, headers=API_HEADERS, timeout=15)
        response.raise_for_status()
        print(f"Lote enviado com sucesso: {response.json()}")
    except requests.RequestException as e:
        print(f"Erro ao enviar lote de trabalho: {e}")

def main_loop():
    print("--- Worker de Precificação (Buff) Iniciado ---")
    print(f"Conectando ao servidor: {API_BASE_URL}")

    while True:
        work_data = get_work_batch()
        
        if not work_data:
            print("Falha ao obter trabalho. Tentando novamente em 60s.")
            time.sleep(60)
            continue
        
        items_to_price = work_data.get("items_to_price", [])
        cny_brl_rate = work_data.get("cny_brl_rate")

        if not items_to_price:
            print("Nenhum item novo para precificar.")
            break
            
        if not cny_brl_rate:
            print("Erro: API não retornou taxa de câmbio. Aguardando 60s.")
            time.sleep(60)
            continue

        print(f"Recebido lote de {len(items_to_price)} itens. Taxa CNY: {cny_brl_rate}")
        results_payload = []
        
        for i, item_job in enumerate(items_to_price):
            item_id = item_job.get("id")
            buff_item_id = item_job.get("buff_item_id")
            
            print(f"  [{i+1}/{len(items_to_price)}] Buscando Buff ID: {buff_item_id}...")
            
            buff_data = call_buff_api(buff_item_id)
            
            if buff_data:
                results_payload.append({
                    "id": item_id,
                    "price_cny": buff_data['price_cny'],
                    "offers": buff_data['offers']
                })
            
            # Pausa para não sobrecarregar a API do Buff
            time.sleep(round(uniform(0, 2), 2))

        # Envia os resultados do lote
        submit_work_batch(results_payload, cny_brl_rate)
        print("Lote concluído. Esperando próximo lote...", end=" ")
        if uniform(0, 1) < 0.5:
            wait_time = randint(900, 1800) # 15-30 minutos
            time.sleep(wait_time)
        else:
            wait_time = randint(120, 300) # Cada worker executa um lote a cada 2-5 minutos
            time.sleep(wait_time)
        print(f"Aguardando {wait_time // 60} minutos...")

if __name__ == "__main__":
    main_loop()