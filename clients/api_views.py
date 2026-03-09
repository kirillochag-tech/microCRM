from rest_framework import generics, permissions
from .models import Client
from .serializers import ClientSerializer

class ClientListView(generics.ListCreateAPIView):
    """
    Получение списка клиентов или создание нового клиента
    """
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Получение, обновление или удаление конкретного клиента
    """
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]