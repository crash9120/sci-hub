import os
import django

# Укажите путь к settings.py вашего проекта
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'makala.settings')
django.setup()

from main.models import Arcticle, ArticleCategory
from django.core.files import File

# Укажите путь к папке с PDF-файлами
pdf_folder = "C:\\Users\\212108\\Downloads\\sci_hub makala skacat etmek un skript\\sci_sckacat"

# ID или экземпляр категории (замените на существующий ID категории)
category = ArticleCategory.objects.first()  # или .get(id=1)

# Проверка, что категория существует
if not category:
    raise Exception("Категория не найдена. Сначала создайте категорию.")

# Перебираем все PDF-файлы в папке
for pdf_file in os.listdir(pdf_folder):
    if pdf_file.endswith(".pdf"):
        file_path = os.path.join(pdf_folder, pdf_file)

        # Название файла без расширения
        title = os.path.splitext(pdf_file)[0]

        # Создаем экземпляр статьи
        article = Arcticle(
            title=title,  # Название файла
            category=category,
            description=f"Файл {pdf_file}",
            user_name="Admin"
        )

        # Добавляем файл
        with open(file_path, 'rb') as f:
            article.file.save(pdf_file, File(f))

        # Сохраняем запись
        article.save()

        print(f"Добавлен файл: {pdf_file} с названием '{title}'")
