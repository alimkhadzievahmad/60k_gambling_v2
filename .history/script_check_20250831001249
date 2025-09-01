import os

# --- НАСТРОЙКИ ---
# Убедись, что этот путь правильный. r'' нужно, чтобы Windows правильно понял путь.
ROOT_DIRECTORY = r"D:\VS\PROJ_60K_PY_V4_GAME"

# Имя файла, в который будут записаны результаты.
OUTPUT_FILE = "downloaded_files_list.txt"
# --- КОНЕЦ НАСТРОЕК ---

all_file_paths = []

# Проверяем, существует ли указанная директория
if not os.path.isdir(ROOT_DIRECTORY):
    print(f"ОШИБКА: Директория не найдена по пути '{ROOT_DIRECTORY}'")
    print("Пожалуйста, проверьте, что путь в переменной ROOT_DIRECTORY указан верно.")
else:
    # Рекурсивно обходим все папки и файлы
    for dirpath, _, filenames in os.walk(ROOT_DIRECTORY):
        for filename in filenames:
            # Формируем полный путь к файлу
            full_path = os.path.join(dirpath, filename)
            all_file_paths.append(full_path)

    # Записываем все найденные пути в файл
    try:
        # Открываем файл в той же папке, где лежит скрипт
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for path in all_file_paths:
                f.write(path + "\n")
        
        print(f"Успешно! Создан файл '{output_path}', содержащий {len(all_file_paths)} путей.")

    except Exception as e:
        print(f"Произошла ошибка при записи в файл: {e}")