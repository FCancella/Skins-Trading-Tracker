# 1. Atualiza o banco com os itens disponiveis (Dash) (a cada 1hr)
# 2. Busca o preço dos itens disponíveis (Buff) (a cada 3 hr)
# 3. Compara e mostra as maiores diferenças de preço

from django.core.management.base import BaseCommand
from datetime import timedelta
from django.utils import timezone
from scanner.models import BlackList, ScannedItem
from scanner.services import dash_bot, dash_p2p, buff
from decimal import Decimal

class Command(BaseCommand):
    help = 'Runs the full scanner script to update Dash items and Buff prices.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Starting Scanner Script ---'))

        # SEÇÃO 1: ATUALIZAR ITENS DA DASH
        self.stdout.write('Step 1: Fetching items from Dash...')
        price_min = 25
        price_max = 500
        products = {} 

        products = dash_p2p.get_items(products, price_min, price_max, 20)
        products = dash_bot.get_items(products, price_min, price_max, 80)

        ScannedItem.objects.filter(source__in=['dash_bot', 'dash_p2p']).delete()
        
        items_to_create = [
            ScannedItem(
                name=name,
                price=info['price'],
                source=info['source']
            ) for name, info in products.items()
        ]
        ScannedItem.objects.bulk_create(items_to_create)
        self.stdout.write(self.style.SUCCESS(f'-> Found and created {len(items_to_create)} items from Dash.'))

        # SEÇÃO 2: ATUALIZAR PREÇOS DO BUFF
        self.stdout.write('Step 2: Updating Buff prices...')

        dash_items_to_check = ScannedItem.objects.filter(source__in=['dash_bot', 'dash_p2p'])
        buff_items_in_db = ScannedItem.objects.filter(source='buff', timestamp__gte=timezone.now()-timedelta(hours=3))
        blacklist_items = BlackList.objects.all().values_list('name', flat=True)

        # Filtra itens da blacklist
        dash_items_to_check = dash_items_to_check.exclude(name__in=blacklist_items)

        # Filtra itens que já têm preço recente do Buff
        recent_buff_names = buff_items_in_db.values_list('name', flat=True)
        items_needing_update = dash_items_to_check.exclude(name__in=recent_buff_names)
        
        self.stdout.write(f'-> Found {items_needing_update.count()} items needing a Buff price update.')

        for index, item in enumerate(items_needing_update):
            buff_info = buff.get_item_info(item.name)
            if buff_info:
                self.stdout.write(f"{index + 1}/{items_needing_update.count()} {item.name}: Buff Price = {buff_info['price']}, Offers = {buff_info['offers']}")
                ScannedItem.objects.create(
                    name=item.name,
                    price=buff_info['price'],
                    offers=buff_info['offers'],
                    source='buff'
                )
                if buff_info.get('offers', 0) < 50:
                    BlackList.objects.update_or_create(
                        name=item.name,
                        defaults={'offers': buff_info['offers']}
                    )

        # SEÇÃO 3: COMPARAR PREÇOS E CALCULAR DIFERENÇA
        self.stdout.write('Step 3: Calculating price differences...')
        
        # Pega todos os itens da Dash que devem ser comparados
        dash_items_to_compare = ScannedItem.objects.filter(source__in=['dash_bot', 'dash_p2p'])
        items_processed = 0

        for dash_item in dash_items_to_compare:
            try:
                # Busca o item correspondente do Buff no banco de dados
                buff_item = ScannedItem.objects.get(source='buff', name=dash_item.name)
                
                # Garante que os preços não sejam nulos ou zero para evitar erros de divisão
                if buff_item.price and dash_item.price and buff_item.price > 0 and dash_item.price > 0:
                    buff_price = Decimal(buff_item.price)
                    dash_price = Decimal(dash_item.price)

                    # Calcula a diferença inicial
                    diff = int((buff_price / dash_price - 1) * 100)
                    
                    # Recalcula com a taxa se a condição for atendida
                    if diff < -7:
                        diff = int((buff_price / (dash_price * Decimal('0.93')) - 1) * 100)
                    
                    # Salva a diferença no registro do item da Dash
                    dash_item.diff = diff
                    buff_item.diff = diff
                    dash_item.save()
                    buff_item.save()
                    items_processed += 1

            except ScannedItem.DoesNotExist:
                # Se não houver um preço do Buff para comparar, pula para o próximo item
                continue
        
        self.stdout.write(self.style.SUCCESS(f'-> Calculated differences for {items_processed} items.'))
        self.stdout.write(self.style.SUCCESS('--- Scanner Script Finished ---'))