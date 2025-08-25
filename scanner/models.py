from django.db import models

class ScannedItem(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offers = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=50)
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