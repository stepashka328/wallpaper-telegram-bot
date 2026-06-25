import os
import json
import time
import requests
from datetime import datetime

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')

# Канал: @wallpaperPCe
CHANNEL_LINK = 'https://t.me/wallpaperPCe'
FILE_PATH = 'posted.json'

# Описание под альбомом
CAPTION = f"""📱 Вертикальные обои для телефона

🔗 Канал: <a href="{CHANNEL_LINK}">wallpaperPCe</a>
#обои #wallpaper #phone #vertical #aesthetic"""

# ================= ФУНКЦИИ РАБОТЫ С ПАМЯТЬЮ =================

def load_posted():
    """Загружает список уже опубликованных ID фото"""
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"📦 Загружено {len(data)} опубликованных фото")
            return data
    except FileNotFoundError:
        print("📄 Файл posted.json не найден, начинаю с чистого листа")
        return []
    except json.JSONDecodeError:
        print("⚠️ Ошибка чтения posted.json, начинаю с чистого листа")
        return []

def save_posted(posted_list):
    """Сохраняет список (только последние 100)"""
    to_save = posted_list[-100:]
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено {len(to_save)} записей в posted.json")

# ================= ПОЛУЧЕНИЕ ОБОЕВ С UNSPLASH =================

def get_wallpapers():
    """Получает вертикальные обои с Unsplash API"""
    if not UNSPLASH_ACCESS_KEY:
        print("❌ Не найден UNSPLASH_ACCESS_KEY в secrets!")
        return []
    
    # Запросы для разнообразия
    queries = [
        'phone wallpaper vertical aesthetic',
        'mobile wallpaper portrait nature',
        'vertical wallpaper abstract',
        'phone background minimalist',
        'vertical landscape wallpaper'
    ]
    
    all_images = []
    
    for query in queries:
        url = 'https://api.unsplash.com/search/photos'
        params = {
            'query': query,
            'per_page': 10,
            'orientation': 'portrait',  # Только вертикальные!
            'client_id': UNSPLASH_ACCESS_KEY
        }
        
        try:
            print(f"🔍 Запрос к Unsplash: {query}")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 401:
                print("❌ Неверный API ключ Unsplash!")
                return []
            elif response.status_code != 200:
                print(f"❌ Ошибка API: {response.status_code}")
                continue
                
            data = response.json()
            photos = data.get('photos', [])
            
            for photo in photos:
                img_info = {
                    'id': photo['id'],
                    'url': photo['urls']['regular'],  # Хорошее качество
                    'download_url': photo['urls']['full'],  # Максимальное
                    'width': photo['width'],
                    'height': photo['height'],
                    'photographer': photo['user']['name']
                }
                
                # Проверяем, что фото действительно вертикальное
                if img_info['height'] > img_info['width']:
                    if img_info['id'] not in [img['id'] for img in all_images]:
                        all_images.append(img_info)
            
            print(f"✅ Найдено {len(photos)} фото по запросу '{query}'")
            
        except Exception as e:
            print(f"❌ Ошибка при запросе '{query}': {e}")
            continue
    
    print(f"🎨 Всего найдено уникальных фото: {len(all_images)}")
    return all_images

# ================= СКАЧИВАНИЕ И ОТПРАВКА =================

def download_image(url):
    """Скачивает изображение в память"""
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")
    return None

def send_album_to_telegram(images_data, caption):
    """Отправляет альбом из 5 фото в Telegram"""
    if len(images_data) < 5:
        print(f"⚠️ Недостаточно фото для альбома (есть {len(images_data)}, нужно 5)")
        return False
    
    # Берем первые 5 фото
    selected_photos = images_data[:5]
    
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup'
    
    # Формируем медиа-группу
    media = []
    downloaded_files = []
    
    for i, photo_info in enumerate(selected_photos):
        print(f"📥 Скачиваю фото {i+1}/5...")
        image_bytes = download_image(photo_info['download_url'])
        
        if not image_bytes:
            print(f"❌ Не удалось скачать фото {i+1}")
            continue
        
        downloaded_files.append(image_bytes)
        
        # Первое фото получает caption, остальные - без
        if i == 0:
            media.append({
                'type': 'photo',
                'media': f'attach://photo_{i}.jpg',
                'caption': caption,
                'parse_mode': 'HTML'
            })
        else:
            media.append({
                'type': 'photo',
                'media': f'attach://photo_{i}.jpg'
            })
    
    if len(downloaded_files) < 5:
        print(f"⚠️ Скачано только {len(downloaded_files)} из 5 фото")
        return False
    
    # Готовим файлы для отправки
    files = {}
    for i, img_bytes in enumerate(downloaded_files):
        files[f'photo_{i}'] = (f'wallpaper_{i}.jpg', img_bytes, 'image/jpeg')
    
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'media': json.dumps(media)
    }
    
    try:
        print("📤 Отправляю альбом в Telegram...")
        response = requests.post(url, files=files, data=data, timeout=60)
        
        if response.status_code == 200:
            print("✅ Альбом успешно отправлен!")
            return True
        else:
            print(f"❌ Ошибка отправки: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")
        return False

# ================= ОСНОВНАЯ ЛОГИКА =================

def main():
    print(f"🚀 Запуск бота для обоев - {datetime.now()}")
    
    # Загружаем историю
    posted = load_posted()
    
    # Получаем обои
    wallpapers = get_wallpapers()
    
    if not wallpapers:
        print("❌ Не удалось получить обои")
        return
    
    # Фильтруем уже опубликованные
    available = [w for w in wallpapers if w['id'] not in posted]
    
    if len(available) < 5:
        print(f"⚠️ Недостаточно новых фото ({len(available)}), очищаю историю")
        posted = []
        available = wallpapers
    
    if len(available) < 5:
        print("❌ Всё равно недостаточно фото для альбома")
        return
    
    print(f"📦 Доступно новых фото: {len(available)}")
    
    # Отправляем альбом
    if send_album_to_telegram(available, CAPTION):
        # Сохраняем ID опубликованных фото
        for photo in available[:5]:
            posted.append(photo['id'])
        save_posted(posted)
        print("🎉 Готово!")
    else:
        print("❌ Не удалось отправить альбом")

if __name__ == '__main__':
    main()
