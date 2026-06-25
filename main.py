import os
import json
import time
import requests
from datetime import datetime

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')

CHANNEL_LINK = 'https://t.me/wallpaperPCe'
FILE_PATH = 'posted.json'

CAPTION = f"""📱 Вертикальные обои для телефона

🔗 Канал: <a href="{CHANNEL_LINK}">wallpaperPCe</a>
#обои #wallpaper #phone #vertical #aesthetic"""

# ================= ФУНКЦИИ РАБОТЫ С ПАМЯТЬЮ =================

def load_posted():
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"📦 Загружено {len(data)} опубликованных фото")
            return data
    except FileNotFoundError:
        print("📄 Файл posted.json не найден")
        return []
    except json.JSONDecodeError:
        print("⚠️ Ошибка чтения posted.json")
        return []

def save_posted(posted_list):
    to_save = posted_list[-100:]
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено {len(to_save)} записей")

# ================= ПОЛУЧЕНИЕ ОБОЕВ (С ОТЛАДКОЙ) =================

def get_wallpapers():
    """Получает вертикальные обои с Unsplash API"""
    
    if not UNSPLASH_ACCESS_KEY:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: UNSPLASH_ACCESS_KEY не найден!")
        return []
    
    print(f"🔑 Ключ Unsplash: {UNSPLASH_ACCESS_KEY[:10]}...")
    
    # 🔍 Простой тестовый запрос
    query = 'wallpaper'
    url = 'https://api.unsplash.com/search/photos'
    
    params = {
        'query': query,
        'per_page': 20,  # Берём больше, чтобы точно найти вертикальные
        'orientation': 'portrait',
        'client_id': UNSPLASH_ACCESS_KEY
    }
    
    print(f"🔍 Запрос: {query}")
    
    try:
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 401:
            print("❌ ОШИБКА 401: Неверный API ключ!")
            return []
        elif response.status_code != 200:
            print(f"❌ Ошибка API: {response.status_code}")
            return []
        
        data = response.json()
        
        # 🔥 ИСПРАВЛЕНИЕ: Unsplash возвращает 'results', а не 'photos'
        photos = data.get('results', [])
        
        print(f"🎨 Найдено фото в ответе: {len(photos)}")
        
        if not photos:
            print("⚠️ Список results пуст")
            return []
        
        # Фильтруем вертикальные и собираем данные
        all_images = []
        for photo in photos:
            try:
                width = photo.get('width', 0)
                height = photo.get('height', 0)
                
                # Проверяем вертикальность (height > width)
                if height <= width:
                    continue
                
                img_info = {
                    'id': photo['id'],
                    'url': photo['urls']['regular'],
                    'download_url': photo['urls']['full'],
                    'width': width,
                    'height': height,
                    'photographer': photo.get('user', {}).get('name', 'Unknown')
                }
                
                # Проверка на дубли
                if img_info['id'] not in [img['id'] for img in all_images]:
                    all_images.append(img_info)
                    
            except (KeyError, TypeError) as e:
                print(f"⚠️ Пропущено фото: {e}")
                continue
        
        print(f"🎯 Итого вертикальных фото: {len(all_images)}")
        return all_images
        
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {e}")
        return []

# ================= СКАЧИВАНИЕ И ОТПРАВКА =================

def download_image(url):
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")
    return None

def send_album_to_telegram(images_data, caption):
    if len(images_data) < 5:
        print(f"⚠️ Недостаточно фото для альбома (есть {len(images_data)}, нужно 5)")
        return False
    
    selected_photos = images_data[:5]
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup'
    
    media = []
    downloaded_files = []
    
    for i, photo_info in enumerate(selected_photos):
        print(f"📥 Скачиваю фото {i+1}/5...")
        image_bytes = download_image(photo_info['download_url'])
        
        if not image_bytes:
            print(f"❌ Не удалось скачать фото {i+1}")
            continue
        
        downloaded_files.append(image_bytes)
        
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
    print(f"🚀 Запуск бота - {datetime.now()}")
    print(f"🔑 TELEGRAM_BOT_TOKEN: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
    print(f"🔑 TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")
    print(f"🔑 UNSPLASH_ACCESS_KEY: {'✅' if UNSPLASH_ACCESS_KEY else '❌'}")
    
    posted = load_posted()
    wallpapers = get_wallpapers()
    
    if not wallpapers:
        print("❌ Не удалось получить обои — см. логи выше")
        return
    
    available = [w for w in wallpapers if w['id'] not in posted]
    
    if len(available) < 5:
        print(f"⚠️ Недостаточно новых фото ({len(available)}), очищаю историю")
        posted = []
        available = wallpapers
    
    if len(available) < 5:
        print("❌ Всё равно недостаточно фото для альбома")
        return
    
    print(f"📦 Доступно новых фото: {len(available)}")
    
    if send_album_to_telegram(available, CAPTION):
        for photo in available[:5]:
            posted.append(photo['id'])
        save_posted(posted)
        print("🎉 Готово!")
    else:
        print("❌ Не удалось отправить альбом")

if __name__ == '__main__':
    main()
