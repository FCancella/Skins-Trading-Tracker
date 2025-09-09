from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class Subscription(models.Model):
    """Armazena o status da assinatura de um usuário."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    mp_payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text="ID do pagamento no Mercado Pago")
    status = models.CharField(max_length=20, default="-")
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.status}"

    @property
    def is_active(self):
        """Verifica se a assinatura está ativa."""
        return self.status == 'approved' and self.end_date and self.end_date > timezone.now()

    @property
    def days_remaining(self):
        """Retorna os dias restantes se a assinatura expirar em 10 dias ou menos."""
        if self.is_active:
            remaining = self.end_date - timezone.now()
            return remaining.days
        return None