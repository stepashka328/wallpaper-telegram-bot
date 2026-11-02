import os
import json
import time
import random
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

# ================= ФУНКЦИИ РАБОТЫ С ПАМЯТЬЮ (УЛУЧШЕНО) =================

def load_posted():
    """Загружает список опубликованных ID с отладкой"""
    try:
        if os.path.exists(FILE_PATH):
            with open(FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📦 Загружено {len(data)} опубликованных ID")
                # Показываем последние 3 для отладки
                if data:
                    print(f"🔍 Последние ID: {data[-3:]}")
                return data
        else:
            print("📄 Файл posted.json не найден, создаю новый")
            return []
    except json.JSONDecodeError as e:
        print(f"⚠️ Ошибка чтения JSON: {e}, начинаю с чистого листа")
        return []
    except Exception as e:
        print(f"⚠️ Неожиданная ошибка: {e}")
        return []

def save_posted(posted_list):
    """Сохраняет список с подтверждением"""
    to_save = list(dict.fromkeys(posted_list))  # Храним ВСЮ историю, без дублей
    try:
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
        print(f"💾 Сохранено {len(to_save)} записей в {FILE_PATH}")
        # Показываем, что именно сохранили
        print(f"🔍 Сохранённые ID (последние 3): {to_save[-3:]}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

# ================= ПОЛУЧЕНИЕ ОБОЕВ =================

def get_wallpapers(posted_ids, need=5):
    """Берёт случайные вертикальные фото с Unsplash (/photos/random),
    пока не наберёт `need` штук, которых ещё не было в канале."""
    if not UNSPLASH_ACCESS_KEY:
        print("❌ UNSPLASH_ACCESS_KEY не найден!")
        return []

    queries = [
        'wallpaper phone vertical',
        'aesthetic wallpaper portrait',
        'minimalist phone background',
        'nature wallpaper mobile',
        'abstract vertical background',
        'dark aesthetic wallpaper',
        'colorful phone wallpaper',
        'gradient background portrait',
    ]
    random.shuffle(queries)  # каждый запуск — свой порядок запросов

    found = []
    seen_ids = set(posted_ids)

    for query in queries:
        params = {
            'query': query,
            'count': 30,               # максимум для /photos/random
            'orientation': 'portrait',
            'content_filter': 'high',
            'client_id': UNSPLASH_ACCESS_KEY,
        }
        try:
            print(f"🎲 Случайные фото по запросу: '{query}'")
            response = requests.get('https://api.unsplash.com/photos/random',
                                    params=params, timeout=15)

            if response.status_code == 401:
                print("❌ ОШИБКА 401: Неверный API ключ!")
                return []
            if response.status_code == 403:
                print("⚠️ Лимит запросов Unsplash исчерпан")
                break
            if response.status_code != 200:
                print(f"⚠️ Ошибка {response.status_code} для '{query}', пропускаю")
                continue

            for photo in response.json():
                try:
                    img_id = str(photo['id'])
                    width = photo.get('width', 0)
                    height = photo.get('height', 0)
                    if height <= width or img_id in seen_ids:
                        continue
                    seen_ids.add(img_id)
                    found.append({
                        'id': img_id,
                        'url': photo['urls']['regular'],
                        'download_url': photo['urls']['full'],
                        'width': width,
                        'height': height,
                    })
                except (KeyError, TypeError):
                    continue
        except Exception as e:
            print(f"⚠️ Ошибка при запросе '{query}': {e}")
            continue

        if len(found) >= need:
            break

    random.shuffle(found)
    print(f"🎯 Новых вертикальных фото: {len(found)}")
    return found

# ================= СКАЧИВАНИЕ И ОТПРАВКА =================

def download_image(url):
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")
    return None

def send_album_to_telegram(images_data, caption):
    if len(images_data) < 5:
        print(f"⚠️ Недостаточно фото (есть {len(images_data)}, нужно 5)")
        return False
    
    selected = images_data[:5]
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup'
    
    downloaded = []
    for i, img_info in enumerate(selected):
        print(f"📥 Скачиваю превью {i+1}/5...")
        img_bytes = download_image(img_info['url'])
        if not img_bytes:
            print(f"❌ Не удалось скачать превью {i+1}")
            return False
        downloaded.append(img_bytes)
    
    media = []
    for i in range(5):
        item = {"type": "photo", "media": f"attach://file{i}"}
        if i == 0:
            item["caption"] = caption
            item["parse_mode"] = "HTML"
        media.append(item)
    
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
    print("\n📦 Отправляю оригиналы в максимальном качестве...")
    selected = images_data[:5]
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument'
    
    for i, img_info in enumerate(selected):
        print(f"📥 Скачиваю оригинал {i+1}/5...")
        img_bytes = download_image(img_info['download_url'])
        
        if not img_bytes:
            print(f"⚠️ Не удалось скачать оригинал {i+1}, пропускаю")
            continue
        
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
            
            time.sleep(1)
        except Exception as e:
            print(f"❌ Ошибка отправки документа {i+1}: {e}")
    
    print("✨ Отправка оригиналов завершена!\n")
    return True

# ================= ОСНОВНАЯ ЛОГИКА =================

def main():
    print(f"🚀 Запуск бота - {datetime.now()}")
    
    # 🔹 Загружаем историю
    posted = load_posted()
    
    # 🔹 Получаем только новые обои (фильтр по истории внутри)
    available = get_wallpapers(posted, need=5)

    if len(available) < 5:
        print(f"❌ Новых фото меньше 5 ({len(available)}), пропускаю этот запуск")
        return

    print(f"📦 Отправляю 5 фото из {len(available)} доступных")
    
    # 🔹 Отправляем альбом
    if send_album_to_telegram(available, CAPTION):
        # 🔹 Отправляем оригиналы
        send_original_files(available)
        
        # 🔹 🔥 ВАЖНО: Сохраняем ID и проверяем результат
        new_ids = [photo['id'] for photo in available[:5]]
        print(f"🔍 Добавляю ID в историю: {new_ids}")
        
        for photo in available[:5]:
            posted.append(photo['id'])
        
        if save_posted(posted):
            print("✅ История успешно сохранена!")
        else:
            print("❌ ОШИБКА: История НЕ сохранена! Проверьте права на запись.")
        
        print("🎉 Готово! Альбом + оригиналы отправлены!")
    else:
        print("❌ Не удалось отправить альбом")

if __name__ == '__main__':
    main()
