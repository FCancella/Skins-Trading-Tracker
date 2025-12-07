from django.core.management.base import BaseCommand
from django.db import transaction
from scanner.models import Item, Collection, Crate


class Command(BaseCommand):
    help = 'Adds vanilla knives to crates/collections based on their associated skins'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("--- Starting vanilla knife assignment ---"))

        try:
            with transaction.atomic():
                self.process_vanilla_knives()
            self.stdout.write(self.style.SUCCESS("--- Vanilla knife assignment completed successfully! ---"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))

    def process_vanilla_knives(self):
        """
        For each vanilla knife, find all crates/collections that contain skins
        with the vanilla knife's name, and add the vanilla to those crates/collections.
        """
        # Get all vanilla knives (items with id starting with "skin-vanilla-weapon_knife")
        vanilla_knives = Item.objects.filter(id__startswith='skin-vanilla-weapon_knife')
        
        if not vanilla_knives.exists():
            self.stdout.write(self.style.WARNING("No vanilla knives found in the database."))
            return
        
        self.stdout.write(f"Found {vanilla_knives.count()} vanilla knife(s).")
        
        ItemCollectionRelation = Item.collections.through
        ItemCrateRelation = Item.crates.through
        
        total_collections_added = 0
        total_crates_added = 0
        
        for vanilla in vanilla_knives:
            self.stdout.write(f"\nProcessing: {vanilla.name} (ID: {vanilla.id})")
            
            # Get all items that start with the vanilla's name
            # For example: "★ Butterfly Knife" -> "★ Butterfly Knife | Fade", etc.
            related_items = Item.objects.filter(name__startswith=vanilla.name).exclude(id=vanilla.id)
            
            if not related_items.exists():
                self.stdout.write(f"  No related skins found for {vanilla.name}")
                continue
            
            self.stdout.write(f"  Found {related_items.count()} related skin(s)")
            
            # Collect all unique collections and crates from related items
            collections_to_add = set()
            crates_to_add = set()
            
            for item in related_items:
                # Get collections this item belongs to
                for collection in item.collections.all():
                    collections_to_add.add(collection.id)
                
                # Get crates this item belongs to
                for crate in item.crates.all():
                    crates_to_add.add(crate.id)
            
            # Get collections/crates the vanilla already belongs to
            existing_collections = set(vanilla.collections.values_list('id', flat=True))
            existing_crates = set(vanilla.crates.values_list('id', flat=True))
            
            # Filter out already existing relationships
            new_collections = collections_to_add - existing_collections
            new_crates = crates_to_add - existing_crates
            
            # Prepare bulk relations to create
            collection_relations = [
                ItemCollectionRelation(item_id=vanilla.id, collection_id=coll_id)
                for coll_id in new_collections
            ]
            
            crate_relations = [
                ItemCrateRelation(item_id=vanilla.id, crate_id=crate_id)
                for crate_id in new_crates
            ]
            
            # Bulk create the relations
            if collection_relations:
                ItemCollectionRelation.objects.bulk_create(collection_relations, ignore_conflicts=True)
                total_collections_added += len(collection_relations)
                self.stdout.write(self.style.SUCCESS(
                    f"  Added {len(collection_relations)} collection(s) to {vanilla.name}"
                ))
            
            if crate_relations:
                ItemCrateRelation.objects.bulk_create(crate_relations, ignore_conflicts=True)
                total_crates_added += len(crate_relations)
                self.stdout.write(self.style.SUCCESS(
                    f"  Added {len(crate_relations)} crate(s) to {vanilla.name}"
                ))
            
            if not collection_relations and not crate_relations:
                self.stdout.write(f"  {vanilla.name} already belongs to all relevant collections/crates")
        
        # Summary
        self.stdout.write(self.style.SUCCESS(
            f"\n=== Summary ===\n"
            f"Total collections added: {total_collections_added}\n"
            f"Total crates added: {total_crates_added}"
        ))
