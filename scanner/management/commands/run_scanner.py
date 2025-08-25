# 1. Atualiza o banco com os itens disponiveis (Dash) (a cada 1hr)
# 2. Busca o preço dos itens disponíveis (Buff) (a cada 3 hr)
# 3. Compara e mostra as maiores diferenças de preço

from django.core.management.base import BaseCommand
from datetime import timedelta
from django.utils import timezone
from scanner.services import dash_bot, dash_p2p, buff
from scanner.models import BlackList, ScannedItem

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

        dash_items = ScannedItem.objects.filter(source='dash_bot')
        buff_items_in_db = ScannedItem.objects.filter(source='buff', timestamp__gte=timezone.now()-timedelta(hours=3))
        blacklist_items = BlackList.objects.all()

        # Filtrando itens da blacklist
        for blacklist_item in blacklist_items:
            if dash_items.filter(name=blacklist_item.name).exists():
                dash_items = dash_items.exclude(name=blacklist_item.name)

        # Filtrando itens que já têm preço recente do Buff
        for dash_item in dash_items:
            if buff_items_in_db.filter(name=dash_item.name).exists():
                dash_items = dash_items.exclude(name=dash_item.name)
        
        self.stdout.write(f'-> Found {dash_items.count()} items needing a Buff price update.')

        # Pegando preços dos itens faltantes
        for index, item in enumerate(dash_items):
            buff_info = buff.get_item_info(item.name)
            if buff_info:
                self.stdout.write(f"{index}/{len(dash_items)} {item.name}: Buff Price = {buff_info['price']}, Offers = {buff_info['offers']}")
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

        self.stdout.write(self.style.SUCCESS('--- Scanner Script Finished ---'))