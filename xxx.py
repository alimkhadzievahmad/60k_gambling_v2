import os
import requests
from urllib.parse import urlparse

# Файл со ссылками
links_file = "links.txt"
# Папка для сохранения скачанных файлов
output_folder = "downloads"
os.makedirs(output_folder, exist_ok=True)

# Заменить базовый URL, если нужно
# Например, заменить "http://example.com/" на "http://newserver.com/"
replace_base_url = {
    # "старый URL": "новый URL"
    "http://localhost:3000/": "https://turboplinko.turbogames.io"
}

# Читаем ссылки
with open(links_file, "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

for url in urls:
    # Применяем замену URL, если нужно
    for old, new in replace_base_url.items():
        if url.startswith(old):
            url = url.replace(old, new, 1)

    # Определяем имя файла из URL
    filename = os.path.basename(urlparse(url).path)
    filepath = os.path.join(output_folder, filename)

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Скачано: {filename}")
    except requests.RequestException as e:
        print(f"Ошибка при скачивании {url}: {e}")
