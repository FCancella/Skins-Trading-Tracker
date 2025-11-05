import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from scanner.models import Item, Collection, Crate

API_URL_SKINS = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json"
API_URL_SKINS_NOT_GROUPED = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins_not_grouped.json"

class Command(BaseCommand):
    help = 'Atualiza a base de dados de itens, coleções e caixas a partir da API ByMykel.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("--- Iniciando atualização da base de dados de itens ---"))

        try:
            item_relations = self.fetch_collections_and_crates()
            self.fetch_all_items(item_relations)
            self.stdout.write(self.style.SUCCESS("--- Atualização concluída com sucesso! ---"))
        
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Erro ao buscar dados da API: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Um erro inesperado ocorreu: {e}"))

    @transaction.atomic
    def fetch_collections_and_crates(self):
        """
        Busca dados da API 'skins.json' para popular os modelos Collection e Crate
        e criar um mapa de relações (item_id -> [collections, crates]).
        """
        self.stdout.write(f"Buscando coleções e caixas de: {API_URL_SKINS}")
        response = requests.get(API_URL_SKINS)
        response.raise_for_status()
        skins_data = response.json()

        item_relations_map = {}
        collections_to_create = []
        crates_to_create = []

        existing_collections = set(Collection.objects.values_list('id', flat=True))
        existing_crates = set(Crate.objects.values_list('id', flat=True))

        for item in skins_data:
            item_id = item.get('id')
            if not item_id:
                continue

            collection_ids = []
            if 'collections' in item:
                for coll in item['collections']:
                    coll_id = coll.get('id')
                    collection_ids.append(coll_id)
                    if coll_id not in existing_collections:
                        collections_to_create.append(
                            Collection(id=coll_id, name=coll.get('name'), image=coll.get('image'))
                        )
                        existing_collections.add(coll_id) # Evita duplicatas na mesma execução

            crate_ids = []
            if 'crates' in item:
                for crate in item['crates']:
                    crate_id = crate.get('id')
                    crate_ids.append(crate_id)
                    if crate_id not in existing_crates:
                        crates_to_create.append(
                            Crate(id=crate_id, name=crate.get('name'), image=crate.get('image'))
                        )
                        existing_crates.add(crate_id) # Evita duplicatas

            item_relations_map[item_id] = {
                'collections': collection_ids,
                'crates': crate_ids
            }

        # Criação em lote
        if collections_to_create:
            Collection.objects.bulk_create(collections_to_create, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"  > Criadas {len(collections_to_create)} novas coleções."))
            
        if crates_to_create:
            Crate.objects.bulk_create(crates_to_create, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"  > Criadas {len(crates_to_create)} novas caixas."))
            
        self.stdout.write("  > Mapa de relações de itens criado.")
        return item_relations_map

    @transaction.atomic
    def fetch_all_items(self, item_relations_map):
        """
        Busca dados da API 'skins_not_grouped.json' para popular o modelo Item.
        Adiciona apenas itens que ainda não existem no banco.
        """
        self.stdout.write(f"Buscando todos os itens de: {API_URL_SKINS_NOT_GROUPED}")
        response = requests.get(API_URL_SKINS_NOT_GROUPED)
        response.raise_for_status()
        all_items_data = response.json()

        existing_item_ids = set(Item.objects.values_list('id', flat=True))
        items_to_create = []
        
        # Listas para relações ManyToMany (M2M)
        ItemCollectionRelation = Item.collections.through
        ItemCrateRelation = Item.crates.through
        collection_relations_to_create = []
        crate_relations_to_create = []

        for item in all_items_data:
            item_id = item.get('id')
            if not item_id or item_id in existing_item_ids:
                continue # Pula itens que já existem ou inválidos

            rarity_name = item.get('rarity', {}).get('name')
            real_rarity = "Covert" if rarity_name == "Extraordinary" else rarity_name
            special = "★" in item.get('name', '')
            real_rarity = "Gold" if special else real_rarity

            new_item = Item(
                id=item_id,
                name=item.get('name'),
                min_float=item.get('min_float'),
                max_float=item.get('max_float'),
                stattrak=item.get('stattrak', False),
                souvenir=item.get('souvenir', False),
                special=special,
                rarity=rarity_name,
                real_rarity=real_rarity,
                market_hash_name=item.get('market_hash_name'),
                image=item.get('image'),
                category=item.get('category', {}).get('name')
            )
            items_to_create.append(new_item)
            
            # Prepara as relações M2M para criação em lote
            base_item_id = item_id.split('_')[0]
            relations = item_relations_map.get(base_item_id)
            
            if relations:
                for coll_id in relations['collections']:
                    collection_relations_to_create.append(
                        ItemCollectionRelation(item_id=item_id, collection_id=coll_id)
                    )
                for crate_id in relations['crates']:
                    crate_relations_to_create.append(
                        ItemCrateRelation(item_id=item_id, crate_id=crate_id)
                    )

        # Cria os itens em lote
        if items_to_create:
            Item.objects.bulk_create(items_to_create, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"  > Criado(s) {len(items_to_create)} novo(s) item(ns)."))
            
            # Cria as relações M2M em lote
            if collection_relations_to_create:
                ItemCollectionRelation.objects.bulk_create(collection_relations_to_create, ignore_conflicts=True)
                self.stdout.write(self.style.SUCCESS(f"  > Adicionadas {len(collection_relations_to_create)} relações de coleção."))
            
            if crate_relations_to_create:
                ItemCrateRelation.objects.bulk_create(crate_relations_to_create, ignore_conflicts=True)
                self.stdout.write(self.style.SUCCESS(f"  > Adicionadas {len(crate_relations_to_create)} relações de caixa."))
        else:
            self.stdout.write(self.style.SUCCESS("  > Nenhum item novo encontrado."))