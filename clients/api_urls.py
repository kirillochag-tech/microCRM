from django.urls import path
from . import api_views

app_name = 'clients_api'

urlpatterns = [
    path('clients/', api_views.ClientListView.as_view(), name='client-list'),
    path('clients/<int:pk>/', api_views.ClientDetailView.as_view(), name='client-detail'),
]