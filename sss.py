import requests

urls = [
    "https://turboplinko.turbogames.io/static/favicons/turboplinko.svg",
]

for url in urls:
    filename = url.split("/")[-1]  # берём имя файла из URL
    print(f"Скачиваем {filename}...")
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"{filename} сохранён.")
    else:
        print(f"Не удалось скачать {filename}, код ошибки: {response.status_code}")
