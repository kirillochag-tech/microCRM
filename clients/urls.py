from django.urls import path
from .views import ClientSearchView, ClientAutocompleteView

app_name = 'clients'

urlpatterns = [
    path('', ClientSearchView.as_view(), name='client_search'),
    path('autocomplete/', ClientAutocompleteView.as_view(), name='client_autocomplete'),
]