from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from clients.models import Client


class ClientSearchView(LoginRequiredMixin, View):
    """API endpoint for searching clients by name (case-insensitive, Cyrillic-safe)."""
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if len(query) < 2:
            return JsonResponse([], safe=False)
        
        # Use icontains - works with Cyrillic in SQLite when case_sensitive_like=OFF (default)
        clients = Client.objects.filter(
            name__icontains=query
        ).only('id', 'name', 'address').distinct()[:20]
        
        data = [{'id': c.id, 'name': c.name, 'address': c.address} for c in clients]
        return JsonResponse(data, safe=False)


class ClientAutocompleteView(LoginRequiredMixin, View):
    """
    Универсальный поиск клиентов с поддержкой кириллицы в SQLite.
    
    Returns a JSON array of client objects: [{'id': int, 'name': str, 'address': str}, ...]
    
    Performs Python-level case folding to ensure Cyrillic case-insensitivity (SQLite limitation).
    Searches in both 'name' and 'trading_point_name' fields.
    
    IMPORTANT: Fetches ALL clients (no 1000 limit) because system handles only hundreds of clients.
    """
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse([], safe=False)
        
        # Fetch ALL clients (no limit)
        all_clients = Client.objects.only('id', 'name', 'trading_point_name', 'address')
        query_casefold = query.casefold()
        matched_clients = []
        
        for c in all_clients:
            name_match = (c.name or '').casefold().find(query_casefold) != -1
            tp_match = (c.trading_point_name or '').casefold().find(query_casefold) != -1
            if name_match or tp_match:
                matched_clients.append(c)
                if len(matched_clients) >= 20:
                    break
        
        client_list = [
            {
                'id': c.id,
                'name': c.name or c.trading_point_name or '',
                'address': c.address or ''
            }
            for c in matched_clients
        ]
        return JsonResponse(client_list, safe=False)