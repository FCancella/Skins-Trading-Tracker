from django.db import models

class ScannedItem(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offers = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=50)
    link = models.URLField(max_length=500, null=True, blank=True)
    diff = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Scanned Item"
        verbose_name_plural = "Scanned Items"

    def __str__(self):
        return self.name

class BlackList(models.Model):
    name = models.CharField(max_length=255)
    offers = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['offers']
        verbose_name = "Blacklisted Item"
        verbose_name_plural = "Blacklisted Items"

    def __str__(self):
        return self.name

class SchedulerLogs(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Scheduler Log"
        verbose_name_plural = "Scheduler Logs"

    def __str__(self):
        return f"Log {self.id} - {self.timestamp}"

class Collection(models.Model):
    """Armazena informações sobre uma coleção de skins."""
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    image = models.URLField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.name

class Crate(models.Model):
    """Armazena informações sobre uma caixa (crate) de skins."""
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    image = models.URLField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.name

WEAR_RANGES = {
    'Factory New': (0.00, 0.07),
    'Minimal Wear': (0.07, 0.15),
    'Field-Tested': (0.15, 0.38),
    'Well-Worn': (0.38, 0.45),
    'Battle-Scarred': (0.45, 1.00),
}

class Item(models.Model):
    """Modelo para armazenar todos os itens do jogo (skins, facas, luvas, etc.)."""
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255, db_index=True)
    min_float = models.FloatField(null=True, blank=True)
    max_float = models.FloatField(null=True, blank=True)
    stattrak = models.BooleanField(default=False)
    souvenir = models.BooleanField(default=False)
    special = models.BooleanField(default=False, help_text="Contém '★' no nome (faca ou luva)")
    rarity = models.CharField(max_length=100, null=True, blank=True)
    real_rarity = models.CharField(max_length=100, null=True, blank=True, help_text="Raridade real (Extraordinary -> Covert)")
    market_hash_name = models.CharField(max_length=255, db_index=True)
    image = models.URLField(max_length=500, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    
    collections = models.ManyToManyField(Collection, related_name="items", blank=True)
    crates = models.ManyToManyField(Crate, related_name="items", blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    offers = models.IntegerField(null=True, blank=True)
    price_time = models.DateTimeField(null=True, blank=True, help_text="Última vez que o preço foi verificado", db_index=True)

    def __str__(self):
        return self.name

    @property
    def real_min_float(self):
        item_min = self.min_float if self.min_float is not None else 0.0
        for wear, (min_w, _) in WEAR_RANGES.items():
            if wear in self.market_hash_name:
                return max(item_min, min_w)
        return item_min

    @property
    def real_max_float(self):
        item_max = self.max_float if self.max_float is not None else 1.0
        for wear, (_, max_w) in WEAR_RANGES.items():
            if wear in self.market_hash_name:
                return min(item_max, max_w)
        return item_max