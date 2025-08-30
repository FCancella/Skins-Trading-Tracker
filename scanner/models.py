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