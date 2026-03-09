"""
Скрипт для обновления геолокации у существующих фото
"""
import os
import sys
import django
from django.conf import settings

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Устанавливаем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tasks.models import PhotoReportItem
from PIL import Image
from PIL.ExifTags import TAGS
import requests
import json


def decimal_to_dms(decimal_degrees):
    """Преобразование десятичных градусов в градусы/минуты/секунды"""
    decimal_degrees = abs(decimal_degrees)
    degrees = int(decimal_degrees)
    minutes_float = (decimal_degrees - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    return (degrees, minutes, seconds)


def dms_to_decimal(degrees, minutes, seconds, direction):
    """Преобразование градусов/минут/секунд в десятичные градусы"""
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal


def extract_gps_info(image_path):
    """Извлечение GPS-информации из EXIF-данных изображения"""
    try:
        img = Image.open(image_path)
        exifdata = img.getexif()
        
        if not exifdata:
            print(f"No EXIF data found in {image_path}")
            return None, None, None
        
        exif_dict = {}
        for tag_id in exifdata:
            tag = TAGS.get(tag_id, tag_id)
            data = exifdata.get(tag_id)
            if isinstance(data, bytes):
                try:
                    data = data.decode()
                except:
                    data = str(data)
            exif_dict[tag] = data

        print(f"DEBUG: Full EXIF dictionary for {image_path}: {exif_dict.keys()}")
        
        # Извлекаем GPS-информацию
        gps_info = exif_dict.get('GPSInfo')
        if not gps_info:
            print(f"No GPSInfo found in EXIF data for {image_path}")
            return None, None, None
            
        print(f"DEBUG: GPSInfo content: {gps_info}")
        
        # Извлекаем широту
        lat_ref = gps_info.get(1)  # GPSLatitudeRef
        lat_values = gps_info.get(2)  # GPSLatitude
        latitude = None
        
        if lat_values and len(lat_values) >= 3:
            # lat_values содержит (градусы, минуты, секунды) в формате дробей
            # Например: [(56, 1), (2, 1), (0, 1)] означает 56° 2' 0"
            lat_deg = float(lat_values[0][0]) / float(lat_values[0][1]) if isinstance(lat_values[0], tuple) else float(lat_values[0])
            lat_min = float(lat_values[1][0]) / float(lat_values[1][1]) if isinstance(lat_values[1], tuple) else float(lat_values[1])
            lat_sec = float(lat_values[2][0]) / float(lat_values[2][1]) if isinstance(lat_values[2], tuple) else float(lat_values[2])
            
            latitude = lat_deg + (lat_min / 60.0) + (lat_sec / 3600.0)
            if lat_ref == 'S':
                latitude = -latitude
            print(f"DEBUG: Calculated latitude: {latitude}")
        else:
            print(f"DEBUG: Insufficient latitude values: {lat_values}")
        
        # Извлекаем долготу
        lon_ref = gps_info.get(3)  # GPSLongitudeRef
        lon_values = gps_info.get(4)  # GPSLongitude
        longitude = None
        
        if lon_values and len(lon_values) >= 3:
            # lon_values содержит (градусы, минуты, секунды) в формате дробей
            lon_deg = float(lon_values[0][0]) / float(lon_values[0][1]) if isinstance(lon_values[0], tuple) else float(lon_values[0])
            lon_min = float(lon_values[1][0]) / float(lon_values[1][1]) if isinstance(lon_values[1], tuple) else float(lon_values[1])
            lon_sec = float(lon_values[2][0]) / float(lon_values[2][1]) if isinstance(lon_values[2], tuple) else float(lon_values[2])
            
            longitude = lon_deg + (lon_min / 60.0) + (lon_sec / 3600.0)
            if lon_ref == 'W':
                longitude = -longitude
            print(f"DEBUG: Calculated longitude: {longitude}")
        else:
            print(f"DEBUG: Insufficient longitude values: {lon_values}")
        
        # Получаем адрес по координатам (обратное геокодирование)
        location_address = None
        if latitude is not None and longitude is not None:
            location_address = reverse_geocode(latitude, longitude)
            if not location_address:
                location_address = 'Не удалось определить адрес'
        
        return latitude, longitude, location_address
        
    except Exception as e:
        print(f"Error extracting GPS info from {image_path}: {e}")
        return None, None, None


def reverse_geocode(lat, lon):
    """
    Обратное геокодирование: получение адреса по координатам
    """
    try:
        # Используем OpenStreetMap Nominatim API
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&accept-language=ru"
        headers = {
            'User-Agent': 'MicroCRM-MCP/1.0'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if 'display_name' in data:
                return data['display_name']
        return None
    except Exception as e:
        print(f"Error in reverse geocoding for ({lat}, {lon}): {e}")
        return None


def update_existing_photos():
    """Обновление геолокации у существующих фото"""
    print("Starting update of existing photos...")
    
    # Получаем все фото отчеты
    photos = PhotoReportItem.objects.all()
    print(f"Found {photos.count()} photos to process")
    
    updated_count = 0
    
    for photo in photos:
        print(f"\nProcessing photo ID {photo.id}: {photo.photo.name}")
        
        if not photo.photo:
            print(f"  Skipping - no photo file")
            continue
            
        # Проверяем, существует ли файл
        if not os.path.exists(photo.photo.path):
            print(f"  Skipping - file does not exist: {photo.photo.path}")
            continue
            
        # Извлекаем геолокацию
        latitude, longitude, location_address = extract_gps_info(photo.photo.path)
        
        # Обновляем запись в базе данных
        photo.latitude = latitude
        photo.longitude = longitude
        photo.location_address = location_address
        
        try:
            photo.save(update_fields=['latitude', 'longitude', 'location_address'])
            print(f"  Updated: Lat={latitude}, Lon={longitude}, Addr={location_address}")
            updated_count += 1
        except Exception as e:
            print(f"  Error saving photo {photo.id}: {e}")
    
    print(f"\nCompleted! Updated {updated_count} photos.")


if __name__ == "__main__":
    update_existing_photos()