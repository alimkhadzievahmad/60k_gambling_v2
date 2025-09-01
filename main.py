import asyncio
import logging
import os
import re
import json
import requests # Теперь импортируется в верхней части для использования в fallback
from urllib.parse import urlparse, urljoin
from pyppeteer import launch
from pyppeteer.errors import NetworkError # Импортируем NetworkError для перехвата специфических ошибок

# --- Конфигурация ---
TARGET_URL = "https://turboplinko.turbogames.io"
# Укажите вашу папку для вывода, куда будут сохраняться все файлы
OUTPUT_DIR = "D:\\VS\\PROJ_60K_PY_V4_GAME" 
LOG_FILE = os.path.join(OUTPUT_DIR, "scraping_log.txt")
# Сколько секунд ждать после загрузки страницы для выполнения всех скриптов
WAIT_AFTER_LOAD_SECONDS = 5 

# --- КОНФИГУРАЦИЯ БРАУЗЕРА (ОЧЕНЬ ВАЖНО) ---
# НУЖНО УКАЗАТЬ ПОЛНЫЙ ПУТЬ к исполняемому файлу Chrome, Chromium или Edge на вашем компьютере.
# Это ОБХОДИТ ошибку загрузки Chromium, используя уже установленный браузер.
#
# Примеры для Windows:
#   Для Google Chrome: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
#   Или, если у вас 32-битная версия Chrome на 64-битной Windows: "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
#   Для Microsoft Edge: "C:\\Program Files (x86)\Microsoft\\Edge\\Application\\msedge.exe"
#
# ЗАМЕНИТЕ СЛЕДУЮЩУЮ СТРОКУ НА ВАШ РЕАЛЬНЫЙ ПУТЬ, ИСПОЛЬЗУЯ "сырую" строку (r"...")
# Это самый простой и надежный способ избежать ошибок с обратными слешами!
CHROME_EXECUTABLE_PATH = r"C:\Users\ADMIN\AppData\Local\Google\Chrome\Application\chrome.exe" 
# Например: CHROME_EXECUTABLE_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


# --- Настройка логирования ---
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True) 

logging.basicConfig(
    level=logging.INFO, # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s', # Формат сообщений в логе
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'), # Логирование в файл
        logging.StreamHandler() # Логирование в консоль
    ]
)
logger = logging.getLogger(__name__)

# --- Сопоставление типов ресурсов с локальными директориями ---
RESOURCE_DIRS = {
    'document': 'html_documents', # Для других HTML документов (не основной страницы)
    'stylesheet': 'css',
    'script': 'js',
    'image': 'images',
    'font': 'fonts',
    'media': 'media',
    'manifest': 'manifests',
    'other': 'other_resources', # Для всего, что не попало в категории
    'xhr': 'api_logs', # Запросы XHR/Fetch будут логироваться отдельно в JSON
    'fetch': 'api_logs',
}

downloaded_urls = set()
api_requests_log = []

# Вспомогательная функция для проверки, является ли Content-Type текстовым
def is_text_content(content_type):
    if not content_type:
        return False
    # Проверяем основные текстовые типы
    text_types = ['text/', 'application/javascript', 'application/json', 'image/svg+xml']
    # Также проверяем кодировки (хотя buffer() обычно работает лучше)
    # Игнорируем специфические бинарные типы, которые могут содержать "text" в названии, но являются бинарными (например, image/webp)
    return any(t in content_type for t in text_types) and not ('image/webp' in content_type)

async def intercept_response(response):
    """Перехватывает сетевые ответы для сохранения ресурсов и логирования API-вызовов."""
    global downloaded_urls, api_requests_log

    url = response.url
    status = response.status
    resource_type = response.request.resourceType
    method = response.request.method
    content_type = response.headers.get('content-type', '').lower()

    logger.info(f"Перехвачен ответ: {method} {resource_type} - Статус: {status} - URL: {url}")

    # Логируем API-вызовы, даже если они неуспешные или не GET, и до сохранения файлов
    if resource_type in ['xhr', 'fetch']:
        try:
            request_post_data = response.request.postData
            response_body_content = ""
            try:
                # Пытаемся получить тело ответа только если статус не 204 (No Content)
                if status != 204:
                    response_body_content = await response.text()
            except NetworkError:
                logger.debug(f"Не удалось получить тело ответа для API-вызова со статусом {status}: {url}")

            api_requests_log.append({
                'url': url,
                'method': method,
                'status': status,
                'request_headers': response.request.headers,
                'request_payload': request_post_data,
                'response_headers': response.headers,
                'response_body': response_body_content
            })
            if status >= 400:
                logger.warning(f"Залогирован API-вызов (Статус: {status}): {url} (ошибка)")
            else:
                logger.info(f"Залогирован API-вызов (Статус: {status}): {url}")
        except Exception as e:
            logger.error(f"Ошибка при логировании API-вызова {url}: {e}", exc_info=True)

    # Пропускаем неуспешные/не-GET ресурсы для сохранения, если это не API-вызов
    if status >= 400 or method != 'GET':
        logger.debug(f"Пропускаем неуспешный/не-GET ресурс для сохранения: {url}")
        return

    # Пропускаем Data-URL (встроенные ресурсы)
    if url.startswith('data:'):
        logger.debug(f"Пропускаем Data-URL: {url}")
        return

    # Проверяем, был ли URL уже скачан
    if url in downloaded_urls:
        logger.debug(f"Пропускаем дубликат URL: {url}")
        return

    # Специальная обработка для основного HTML-документа
    if url == TARGET_URL and resource_type == 'document':
        # Основной HTML будет сохранен позже методом page.content() для получения отрендеренного DOM
        downloaded_urls.add(url)
        return

    try:
        # Определяем локальную директорию для сохранения
        base_dir_name = RESOURCE_DIRS.get(resource_type, 'other_resources')
        local_dir = os.path.join(OUTPUT_DIR, base_dir_name)
        os.makedirs(local_dir, exist_ok=True)

        # Генерируем имя файла
        parsed_url = urlparse(url)
        path_segments = [s for s in parsed_url.path.split('/') if s]
        filename_base = path_segments[-1] if path_segments else None
        
        # Более надежное определение имени файла и расширения
        filename = filename_base
        if not filename or '.' not in filename: # Если имени нет или нет явного расширения
            if resource_type == 'document':
                filename = 'document.html'
            elif resource_type == 'stylesheet':
                filename = 'style.css'
            elif resource_type == 'script':
                filename = 'script.js'
            elif resource_type == 'font':
                # Пытаемся угадать расширение шрифта по content-type
                if 'woff2' in content_type: filename = 'font.woff2'
                elif 'woff' in content_type: filename = 'font.woff'
                elif 'truetype' in content_type: filename = 'font.ttf'
                elif 'opentype' in content_type: filename = 'font.otf'
                else: filename = 'font.bin'
            elif resource_type == 'image':
                # Пытаемся угадать по content-type
                if 'image/png' in content_type: filename = 'image.png'
                elif 'image/jpeg' in content_type: filename = 'image.jpg'
                elif 'image/svg' in content_type: filename = 'image.svg'
                elif 'image/webp' in content_type: filename = 'image.webp'
                elif 'image/gif' in content_type: filename = 'image.gif'
                else: filename = 'image.bin'
            elif resource_type == 'media':
                 if 'video/mp4' in content_type: filename = 'video.mp4'
                 elif 'video/' in content_type: filename = 'video.bin'
                 elif 'audio/' in content_type: filename = 'audio.bin'
                 else: filename = 'media.bin'
            else:
                filename = 'resource.bin' # Fallback для всего остального
            
            # Добавляем уникальность, если дефолтное имя без уникализации может быть дублировано
            # Делаем это, если исходное имя было сгенерировано (нет базового имени)
            if not filename_base:
                name, ext = os.path.splitext(filename)
                unique_suffix = f"_{hash(url) % 100000}" # Более длинный хэш для уникальности
                filename = f"{name}{unique_suffix}{ext}"


        # Добавляем суффикс, если файл с таким именем уже существует (для уникальности)
        local_filepath = os.path.join(local_dir, filename)
        if os.path.exists(local_filepath):
            name, ext = os.path.splitext(filename)
            unique_suffix = f"_{hash(url) % 100000}" # Используем более длинный хэш для уникальности
            filename = f"{name}{unique_suffix}{ext}"
            local_filepath = os.path.join(local_dir, filename)
        
        file_content = None
        file_mode = 'wb' # По умолчанию бинарный режим
        file_encoding = None

        if is_text_content(content_type):
            file_mode = 'w'
            file_encoding = 'utf-8'

        try:
            if file_mode == 'w':
                file_content = await response.text()
            else:
                file_content = await response.buffer()
        except NetworkError as ne:
            logger.warning(f"Ошибка сети Pyppeteer при получении содержимого ресурса {url}: {ne}. Попытка получить через requests (fallback).")
            # Fallback к requests library
            headers = {k.lower(): v for k, v in response.request.headers.items()}
            # Удаляем 'accept-encoding' из заголовков запроса, чтобы requests сам обрабатывал сжатие
            headers.pop('accept-encoding', None) 
            try:
                # Используем stream=True для больших файлов и читаем по частям
                with requests.get(url, headers=headers, stream=True, timeout=10) as r:
                    r.raise_for_status() # Вызывает HTTPError для плохих ответов (4xx или 5xx)
                    if file_mode == 'w':
                        file_content = r.text
                    else:
                        file_content = b''.join(r.iter_content(chunk_size=8192)) # Читаем бинарные данные по частям
                logger.info(f"Ресурс {url} успешно загружен через requests (fallback).")
            except Exception as req_e:
                logger.error(f"Не удалось сохранить ресурс {url} даже через requests (fallback): {req_e}", exc_info=True)
                return # Пропускаем сохранение, если fallback также не удался

        if file_content is None:
             logger.error(f"Содержимое ресурса {url} оказалось None после всех попыток получения.")
             return

        # Запись содержимого в файл
        with open(local_filepath, file_mode, encoding=file_encoding) as f:
            f.write(file_content)
        
        downloaded_urls.add(url)
        logger.info(f"Сохранен ресурс ({resource_type}, {file_mode}): {url} -> {local_filepath}")

    except Exception as e:
        logger.error(f"Ошибка при сохранении ресурса {url}: {e}", exc_info=True)


async def scrape_website():
    """Основная функция для запуска браузера, навигации, скрапинга и сохранения."""
    logger.info(f"Начало процесса скрапинга для: {TARGET_URL}")

    # Создаем все необходимые выходные директории
    for dir_name in set(RESOURCE_DIRS.values()):
        os.makedirs(os.path.join(OUTPUT_DIR, dir_name), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, 'html_full_rendered'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, 'html_raw'), exist_ok=True)

    browser = None
    try:
        # Конфигурация запуска браузера
        launch_options = {
            'headless': True, 
            'args': ['--no-sandbox', '--disable-setuid-sandbox']
        }

        # Используем указанный путь к исполняемому файлу браузера
        if CHROME_EXECUTABLE_PATH and "### ВСТАВЬТЕ СЮДА" not in CHROME_EXECUTABLE_PATH:
            if not os.path.exists(CHROME_EXECUTABLE_PATH):
                logger.error(f"Указанный путь к браузеру не существует: {CHROME_EXECUTABLE_PATH}")
                logger.error("Пожалуйста, проверьте CHROME_EXECUTABLE_PATH в файле main.py.")
                return
            logger.info(f"Использование указанного браузера: {CHROME_EXECUTABLE_PATH}")
            launch_options['executablePath'] = CHROME_EXECUTABLE_PATH
        else:
            logger.error("CHROME_EXECUTABLE_PATH не был указан или имеет placeholder.")
            logger.error("Вам нужно изменить строку 'CHROME_EXECUTABLE_PATH = \"### ВСТАВЬТЕ СЮДА...\"' в файле main.py на фактический путь к вашему Chrome/Edge.")
            logger.error("Пример: CHROME_EXECUTABLE_PATH = r\"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\"")
            return

        logger.info("Запуск браузера Chromium (или указанного вами)...")
        browser = await launch(**launch_options)
        page = await browser.newPage()

        # Устанавливаем User-Agent, чтобы имитировать обычный браузер
        await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36")

        # Включаем перехват запросов для сохранения ресурсов и логирования API-вызовов
        page.on('response', lambda res: asyncio.ensure_future(intercept_response(res)))

        logger.info(f"Навигация к {TARGET_URL} и ожидание полной загрузки страницы...")
        # Увеличил таймаут до 60 секунд, чтобы дать больше времени для загрузки
        response = await page.goto(TARGET_URL, waitUntil='networkidle2', timeout=60000) 
        
        if response.status >= 400:
            logger.error(f"Не удалось загрузить страницу {TARGET_URL}. Статус: {response.status}")
            logger.error(f"Тело ответа: {await response.text()}")
            return

        logger.info(f"Страница успешно загружена. Ожидание {WAIT_AFTER_LOAD_SECONDS} секунд для выполнения динамического контента...")
        await asyncio.sleep(WAIT_AFTER_LOAD_SECONDS) 

        # --- Сохраняем полностью отрендеренный HTML (DOM после выполнения JS) ---
        full_html_content = await page.content()
        html_filepath = os.path.join(OUTPUT_DIR, 'html_full_rendered', 'index.html')
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(full_html_content)
        logger.info(f"Сохранен полностью отрендеренный HTML в: {html_filepath}")

        # --- Сохраняем исходный HTML (до выполнения JS) для сравнения ---
        try:
            logger.info("Попытка получить исходный HTML страницы (до выполнения JS) с помощью requests...")
            # Используем тот же User-Agent, что и в браузере
            raw_html_response = requests.get(TARGET_URL, headers={'User-Agent': await page.evaluate('navigator.userAgent')})
            if raw_html_response.status_code == 200:
                raw_html_filepath = os.path.join(OUTPUT_DIR, 'html_raw', 'index_raw.html')
                with open(raw_html_filepath, 'w', encoding='utf-8') as f:
                    f.write(raw_html_response.text)
                logger.info(f"Сохранен исходный HTML в: {raw_html_filepath}")
            else:
                logger.warning(f"Не удалось получить исходный HTML, статус: {raw_html_response.status_code}")
        except Exception as e:
            logger.warning(f"Не удалось получить исходный HTML с помощью requests: {e}")

        # --- Сохраняем лог API-запросов ---
        if api_requests_log:
            api_log_filepath = os.path.join(OUTPUT_DIR, 'api_logs', 'api_requests.json')
            with open(api_log_filepath, 'w', encoding='utf-8') as f:
                json.dump(api_requests_log, f, indent=4, ensure_ascii=False)
            logger.info(f"Сохранен лог API-запросов в: {api_log_filepath}")
        else:
            logger.info("Не перехвачено значимых API-запросов (XHR/Fetch).")

        logger.info("Процесс скрапинга успешно завершен.")

    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка во время скрапинга: {e}", exc_info=True)
    finally:
        if browser:
            await browser.close()
            logger.info("Браузер закрыт.")

if __name__ == "__main__":
    logger.info("Скрипт запущен.")
    if "### ВСТАВЬТЕ СЮДА" in CHROME_EXECUTABLE_PATH:
        logger.error("ПУТЬ К БРАУЗЕРУ НЕ УКАЗАН! Пожалуйста, отредактируйте переменную CHROME_EXECUTABLE_PATH в main.py.")
        logger.error("Пример: CHROME_EXECUTABLE_PATH = r\"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\"")
    else:
        # Использование asyncio.run() для запуска основной асинхронной функции (современный способ)
        asyncio.run(scrape_website())