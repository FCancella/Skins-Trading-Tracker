from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
import math

class Store(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='store')
    name = models.CharField(max_length=100, default="Minha Loja", verbose_name="Nome da Loja")
    steam_id = models.CharField(max_length=64, help_text="Steam ID64 do vendedor")
    fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.0, verbose_name="Taxa (%)")
    whatsapp = models.CharField(max_length=20, help_text="Número com DDD para contato", blank=True, null=True)
    
    def __str__(self):
        return f"{self.name}"

class StoreItem(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Base")
    image_url = models.URLField(max_length=500, blank=True, null=True)
    is_visible = models.BooleanField(default=True, verbose_name="Visível na Loja")

    @property
    def price(self):
        """
        Calcula o preço final dinamicamente baseando-se na taxa atual da loja.
        Fórmula: Base * (1 + Taxa/100), arredondado pra cima (final 0 ou 5).
        """
        if not self.base_price:
            return Decimal(0)
        
        # Pega a taxa atual da loja vinculada
        fee = float(self.store.fee_percentage)
        base = float(self.base_price)
        
        val = base * (1 + (fee / 100))
        
        # Lógica de arredondamento (ceil para múltiplo de 5)
        final = math.ceil(val / 5) * 5
        return Decimal(final).quantize(Decimal("0.01"))

    @property
    def tax_amount(self):
        """Retorna o valor monetário da taxa (Preço Final - Preço Base)"""
        if self.base_price:
            return self.price - self.base_price
        return Decimal(0)

    def __str__(self):
        return f"{self.name} - R$ {self.price}"