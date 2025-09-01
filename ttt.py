import re

# Укажи путь к твоему файлу с логами
input_file = "logs.txt"
# Файл, куда будем сохранять найденные ссылки
output_file = "links.txt"

# Регулярное выражение для поиска ссылок
url_pattern = r"https?://[^\s]+"

with open(input_file, "r", encoding="utf-8") as f:
    content = f.read()

# Ищем все ссылки
urls = re.findall(url_pattern, content)

# Убираем дубликаты (если нужно)
urls = list(set(urls))

# Сохраняем в файл
with open(output_file, "w", encoding="utf-8") as f:
    for url in urls:
        f.write(url + "\n")

print(f"Найдено {len(urls)} уникальных ссылок. Сохранено в {output_file}.")
