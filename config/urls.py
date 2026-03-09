# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users.views import LoginView, LogoutView, DashboardView
from .favicon import favicon

urlpatterns = [
    path('favicon.ico', favicon, name='favicon'),
    path('admin/', admin.site.urls),
    path('', DashboardView.as_view(), name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # App URLs
    path('users/', include('users.urls')),
    path('tasks/', include('tasks.urls', namespace='tasks')),
    path('api/clients/search/', include('clients.urls', namespace='clients_search_api')),
    path('clients/', include('clients.urls', namespace='clients')),
    path('reports/', include('reports.urls')),  # Убедитесь, что эта строка есть
    path('announcements/', include('announcements.urls')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('api/notifications/', include('notifications.api_urls', namespace='notifications_api')),
    path('api/tasks/', include('tasks.api_urls', namespace='tasks_api')),
    path('api/clients/', include('clients.api_urls', namespace='clients_rest_api')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Обслуживание статических файлов из STATICFILES_DIRS при DEBUG
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")