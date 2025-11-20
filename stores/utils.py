import requests
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from scanner.models import ScannedItem
from scanner.services import buff
import time

def get_steam_inventory(steam_id):
    """
    Busca o inventário CS2 do usuário.
    Retorna lista de dicts: {'name': str, 'image': str, 'type': str}
    """
    url = f"https://steamcommunity.com/inventory/{steam_id}/730/2"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                descriptions = {d['classid'] + '_' + d['instanceid']: d for d in data.get('descriptions', [])}
                inventory = []
                
                for asset in data.get('assets', []):
                    key = asset['classid'] + '_' + asset['instanceid']
                    desc = descriptions.get(key)
                    
                    if desc and desc.get('marketable', 0) == 1:
                        icon_url = desc.get('icon_url')
                        image = f"https://community.cloudflare.steamstatic.com/economy/image/{icon_url}" if icon_url else None
                        
                        inventory.append({
                            'name': desc.get('market_hash_name'),
                            'image': image,
                            'type': desc.get('type', '') 
                        })
                return inventory
    except Exception as e:
        print(f"Erro ao buscar inventário: {e}")
    return []

def get_item_base_price(item_name):
    """
    Busca o PREÇO BASE do item.
    Retorna Decimal(price) ou Decimal(0) se não encontrado ou < 10.
    """
    
    # 1. Verificação de segurança: Item muito barato no último mês?
    month_ago = timezone.now() - timedelta(days=30)
    recent_history = ScannedItem.objects.filter(
        name=item_name,
        timestamp__gte=month_ago
    ).order_by('-timestamp').first()

    ignore = ['Sticker', 'Case', 'Container', 'Graffiti', 'Souvenir', 'Charm']

    if (recent_history and recent_history.price < 10) or any(ignore in item_name for ignore in ignore):
        return Decimal(0)  # Ignora item barato baseado no histórico

    # 2. Busca preço base recente (últimas 72h)
    limit_date = timezone.now() - timedelta(hours=72)
    scanned = ScannedItem.objects.filter(
        name=item_name, 
        timestamp__gte=limit_date
    ).order_by('-timestamp').first()

    base_price = 0.0

    if scanned:
        base_price = float(scanned.price)
    else:
        # 3. Fallback para Buff API
        
        time.sleep(5)

        buff_data = buff.get_item_info(item_name)
        print(f"Buff data para {item_name}: {buff_data}")
        
        if buff_data and 'price' in buff_data:
            base_price = buff_data['price']
            
            # Salva no banco para cache
            try:
                ScannedItem.objects.create(
                    name=item_name,
                    price=base_price,
                    offers=buff_data.get('offers'),
                    source='buff',
                    link=buff_data.get('link')
                )
            except Exception as e:
                print(f"Erro ao salvar ScannedItem para {item_name}: {e}")
    
    # 4. Verifica se o preço base é válido (> 10)
    if base_price < 10:
        return Decimal(0)

    return Decimal(base_price)