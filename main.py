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
                
                img_info = {
                    'id': photo['id'],
                    'url': photo['urls']['regular'],  # Для превью (1080px)
                    'download_url': photo['urls']['full'],  # Оригинал (макс. качество)
                    'width': width,
                    'height': height,
                }
                
                if img_info['id'] not in [img['id'] for img in all_images]:
                    all_images.append(img_info)
                    
            except (KeyError, TypeError):
                continue
        
        print(f"🎯 Вертикальных фото: {len(all_images)}")
        return all_images
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

# ================= СКАЧИВАНИЕ И ОТПРАВКА =================

def download_image(url):
    try:
        response = requests.get(url, timeout=30)  # Увеличил таймаут для больших файлов
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")
    return None

def send_album_to_telegram(images_data, caption):
    """Отправляет альбом из 5 фото (сжатое качество для превью)"""
    if len(images_data) < 5:
        print(f"⚠️ Недостаточно фото (есть {len(images_data)}, нужно 5)")
        return False
    
    selected = images_data[:5]
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup'
    
    # Скачиваем фото (regular качество)
    downloaded = []
    for i, img_info in enumerate(selected):
        print(f"📥 Скачиваю превью {i+1}/5...")
        img_bytes = download_image(img_info['url'])  # Regular quality
        if not img_bytes:
            print(f"❌ Не удалось скачать превью {i+1}")
            return False
        downloaded.append(img_bytes)
    
    # Формируем media array
    media = []
    for i in range(5):
        item = {"type": "photo", "media": f"attach://file{i}"}
        if i == 0:
            item["caption"] = caption
            item["parse_mode"] = "HTML"
        media.append(item)
    
    # Готовим multipart/form-data
    files = {
        "chat_id": (None, TELEGRAM_CHAT_ID),
        "media": (None, json.dumps(media, ensure_ascii=False))
    }
    for i, img_bytes in enumerate(downloaded):
        files[f"file{i}"] = (f"wallpaper_{i}.jpg", img_bytes, "image/jpeg")
    
    try:
        print("📤 Отправляю альбом (превью)...")
        response = requests.post(url, files=files, timeout=60)
        
        if response.status_code == 200:
            print("✅ Альбом отправлен!")
            return True
        else:
            print(f"❌ Ошибка {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение при отправке: {e}")
        return False

def send_original_files(images_data):
    """Отправляет оригиналы фото как документы (без сжатия)"""
    print("\n📦 Отправляю оригиналы в максимальном качестве...")
    
    selected = images_data[:5]
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument'
    
    for i, img_info in enumerate(selected):
        print(f"📥 Скачиваю оригинал {i+1}/5...")
        img_bytes = download_image(img_info['download_url'])  # Full quality
        
        if not img_bytes:
            print(f"⚠️ Не удалось скачать оригинал {i+1}, пропускаю")
            continue
        
        # Отправляем как документ (без сжатия)
        files = {
            'document': (f'wallpaper_original_{i+1}.jpg', img_bytes, 'image/jpeg'),
            'chat_id': (None, TELEGRAM_CHAT_ID),
            'caption': (None, f'📸 Оригинал #{i+1}\nРазмер: {img_info["width"]}x{img_info["height"]}')
        }
        
        try:
            print(f"📤 Отправляю документ {i+1}/5...")
            response = requests.post(url, files=files, timeout=60)
            
            if response.status_code == 200:
                print(f"✅ Оригинал {i+1} отправлен")
            else:
                print(f"⚠️ Ошибка при отправке оригинала {i+1}: {response.status_code}")
            
            # Пауза между отправками (чтобы Telegram не спамил)
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Ошибка отправки документа {i+1}: {e}")
    
    print("✨ Отправка оригиналов завершена!\n")
    return True

# ================= ОСНОВНАЯ ЛОГИКА =================

def main():
    print(f"🚀 Запуск бота - {datetime.now()}")
    
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
    
    # 1️⃣ Отправляем альбом (превью)
    if send_album_to_telegram(available, CAPTION):
        # 2️⃣ Отправляем оригиналы как документы
        send_original_files(available)
        
        # 3️⃣ Сохраняем в историю
        for photo in available[:5]:
            posted.append(photo['id'])
        save_posted(posted)
        
        print("🎉 Готово! Альбом + оригиналы отправлены!")
    else:
        print("❌ Не удалось отправить альбом")

if __name__ == '__main__':
    main()
