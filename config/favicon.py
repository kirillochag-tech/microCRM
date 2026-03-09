from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.templatetags.static import static
from django.conf import settings
import os


from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.templatetags.static import static
from django.conf import settings
import os
from pathlib import Path

@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # Cache for 24 hours
def favicon(request):
    """
    Serve the favicon.ico file.
    """
    import mimetypes
    
    # Путь к favicon.ico в папке static/img
    base_dir = Path(settings.BASE_DIR)
    favicon_path = base_dir / "static" / "img" / "favicon.ico"
    
    if favicon_path.exists():
        with open(favicon_path, 'rb') as f:
            content = f.read()
        
        # Возвращаем с правильным MIME-типом для favicon
        return HttpResponse(content, content_type='image/x-icon')
    else:
        # Return a simple 1x1 transparent PNG as fallback
        # Base64 encoded 1x1 transparent PNG
        png_data = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
        import base64
        content = base64.b64decode(png_data)
        return HttpResponse(content, content_type='image/png')