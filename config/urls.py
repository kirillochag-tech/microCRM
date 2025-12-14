# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users.views import LoginView, LogoutView, DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', DashboardView.as_view(), name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # App URLs
    path('users/', include('users.urls')),
    path('tasks/', include('tasks.urls')),
    path('api/clients/search/', include('clients.urls')),
    path('clients/', include('clients.urls')),
    path('reports/', include('reports.urls')),  # Убедитесь, что эта строка есть
    path('announcements/', include('announcements.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)