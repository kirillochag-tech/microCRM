from django.http import JsonResponse
from django.views import View
from clients.models import Client
import re


class ClientSearchView(View):
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse([], safe=False)
        
        # Using iregex for truly case-insensitive search that works reliably with Cyrillic
        escaped_query = re.escape(query)  # Properly escape special regex characters
        clients = Client.objects.filter(
            name__iregex=escaped_query
        ).distinct()[:20]
        
        data = [{'id': c.id, 'name': c.name} for c in clients]
        return JsonResponse(data, safe=False)