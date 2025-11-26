from rest_framework import viewsets, permissions
from trades.models import Trade
from .serializers import TradeSerializer

class TradeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows trades to be viewed or edited.
    """
    serializer_class = TradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return trades belonging to the current user
        return Trade.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # Automatically set the owner to the current user
        serializer.save(owner=self.request.user)