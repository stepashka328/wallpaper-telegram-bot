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

# ================= ПОЛУЧЕНИЕ ОБОЕВ =================

def get_wallpapers():
    if not UNSPLASH_ACCESS_KEY:
        print("❌ UNSPLASH_ACCESS_KEY не найден!")
        return []
    
    query = 'wallpaper'
    url = 'https://api.unsplash.com/search/photos'
    params = {
        'query': query,
        'per_page': 20,
        'orientation': 'portrait',
        'client_id': UNSPLASH_ACCESS_KEY
    }
    
    try:
        print(f"🔍 Запрос: {query}")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 401:
            print("❌ ОШИБКА 401: Неверный API ключ!")
            return []
        elif response.status_code != 200:
            print(f"❌ Ошибка API: {response.status_code}")
            return []
        
        data = response.json()
        photos = data.get('results', [])
        
        print(f"🎨 Найдено фото: {len(photos)}")
        if not photos:
            return []
        
        all_images = []
        for photo in photos:
            try:
                width = photo.get('width', 0)
                height = photo.get('height', 0)
                
                # Только вертикальные
                if height <= width:
                    continue
                
                # ✅ Используем 'regular' (1080px) - быстрее грузится, идеально для телефонов
                img_info = {
                    'id': photo['id'],
                    'url': photo['urls']['regular'],
                    'width': width,
                    'height': height,
                }
                
                if img_info['id'] not in [img['id'] for img in all_images]:
                    all_images.append(img_info)
                    
            except (KeyError, TypeError):
                continue
        
        print(f" Вертикальных фото: {len(all_images)}")
        return all_images
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

# ================= СКАЧИВАНИЕ И ОТПРАВКА АЛЬБОМА (ИСПРАВЛЕНО) =================

def download_image(url):
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")
    return None

def send_album_to_telegram(images_data, caption):
    """Отправляет альбом из 5 фото через скачивание и attach:// (надёжно)"""
    if len(images_data) < 5:
        print(f"⚠️ Недостаточно фото (есть {len(images_data)}, нужно 5)")
        return False
    
    selected = images_data[:5]
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup'
    
    # 1️⃣ Скачиваем все 5 фото
    downloaded = []
    for i, img_info in enumerate(selected):
        print(f"📥 Скачиваю фото {i+1}/5...")
        img_bytes = download_image(img_info['url'])
        if not img_bytes:
            print(f" Не удалось скачать фото {i+1}")
            return False
        downloaded.append(img_bytes)
    
    # 2️⃣ Формируем media array для Telegram API
    media = []
    for i in range(5):
        item = {"type": "photo", "media": f"attach://file{i}"}
        if i == 0:
            item["caption"] = caption
            item["parse_mode"] = "HTML"
        media.append(item)
    
    # 3️⃣ Готовим multipart/form-data
    # chat_id и media отправляются как текстовые поля, файлы - как бинарные
    files = {
        "chat_id": (None, TELEGRAM_CHAT_ID),
        "media": (None, json.dumps(media, ensure_ascii=False))
    }
    for i, img_bytes in enumerate(downloaded):
        files[f"file{i}"] = (f"wallpaper_{i}.jpg", img_bytes, "image/jpeg")
    
    # 4️ Отправляем
    try:
        print("📤 Отправляю альбом в Telegram...")
        response = requests.post(url, files=files, timeout=60)
        
        if response.status_code == 200:
            print("✅ Альбом успешно отправлен!")
            return True
        else:
            print(f"❌ Ошибка {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение при отправке: {e}")
        return False

# ================= ОСНОВНАЯ ЛОГИКА =================

def main():
    print(f" Запуск бота - {datetime.now()}")
    
    posted = load_posted()
    wallpapers = get_wallpapers()
    
    if not wallpapers:
        print("❌ Не удалось получить обои")
        return
    
    available = [w for w in wallpapers if w['id'] not in posted]
    
    if len(available) < 5:
        print(f"⚠️ Недостаточно новых фото ({len(available)}), очищаю историю")
        posted = []
        available = wallpapers
    
    if len(available) < 5:
        print("❌ Недостаточно фото для отправки")
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
