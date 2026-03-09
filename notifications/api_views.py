from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib.auth import get_user_model
from .models import Notification
from .serializers import NotificationSerializer

User = get_user_model()

class NotificationListView(generics.ListAPIView):
    """
    Получение списка уведомлений текущего пользователя
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')


class NotificationDetailView(generics.RetrieveAPIView):
    """
    Получение деталей конкретного уведомления
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


@api_view(['POST'])
def mark_notification_as_read(request, pk):
    """
    Отметить уведомление как прочитанное
    """
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def mark_all_notifications_as_read(request):
    """
    Отметить все уведомления текущего пользователя как прочитанные
    """
    if request.method == 'POST':
        Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_unread_notifications_count(request):
    """
    Получить количество непрочитанных уведомлений
    """
    if request.method == 'GET':
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count}, status=status.HTTP_200_OK)