from django.conf import settings
from django.urls import reverse
from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404, HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import ArticleForm
from django.db.models import Count
from django.core.paginator import Paginator
from random import sample
from .models import Article, ArticleCategory, Article_like, Article_read, Article_comment, Contact
from PIL import Image
import os
import shutil
import re
import pdfplumber
import atexit
import threading
import fitz  # PyMuPDF
import logging
import zipfile
import uuid
import io
import pytesseract
import csv
import tempfile
from crossref.restful import Works
import warnings
import mimetypes

# Настройка логирования для отладки
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Отключаем предупреждения CropBox
warnings.filterwarnings("ignore", category=UserWarning, module="pdfplumber")

def get_most_liked_articles(num_articles=5):
    most_liked_articles = Article_like.objects.values('article_like') \
        .annotate(like_count=Count('id')) \
        .order_by('-like_count')[:num_articles]
    
    article_ids = [item['article_like'] for item in most_liked_articles]
    most_liked_articles = Article.objects.filter(id__in=article_ids)
    return most_liked_articles

def index(request):
    user = request.user
    is_auth = user.is_authenticated

    if is_auth:
        read_articles_qs = Article_read.objects.filter(user=user)
        liked_articles_qs = Article_like.objects.filter(user=user)
        read_articles_count = read_articles_qs.count()
        user_read_articles = read_articles_qs.values_list('article_read_id', flat=True)
        user_liked_articles = liked_articles_qs.values_list('article_like_id', flat=True)
        articles = Article.objects.filter(user_name__icontains=user.username)
    else:
        read_articles_count = 0
        user_read_articles = []
        user_liked_articles = []
        articles = Article.objects.all()

    user_count = User.objects.count()
    article_count = Article.objects.count()
    all_articles = list(Article.objects.all())
    random_articles = sample(all_articles, min(len(all_articles), 30))
    categories = ArticleCategory.objects.annotate(article_count=Count('articles'))

    context = {
        'user_count': user_count,
        'article_count': article_count,
        'random_articles': random_articles,
        'read_articles_count': read_articles_count,
        'user_read_articles': user_read_articles,
        'user_liked_articles': user_liked_articles,
        'categories': categories,
    }
    return render(request, 'index.html', context)

def article_list(request):
    article_list = None
    if request.method == 'POST':
        article = request.POST['article']
        article_list = Article.objects.filter(title__icontains=article)
    else:
        article_list = Article.objects.all()

    paginator = Paginator(article_list, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = ArticleCategory.objects.all()

    context = {
        'article_list': page_obj,
        'categories': categories
    }
    return render(request, 'article.html', context)

def article_by_category(request, category_id):
    articles = Article.objects.filter(category_id=category_id)
    categories = ArticleCategory.objects.annotate(article_count=Count('articles'))
    
    paginator = Paginator(articles, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'article_list': page_obj,
        'categories': categories
    }
    return render(request, 'article.html', context)
    
@login_required
def liked(request, article_id):
    article = Article.objects.filter(id=article_id).first()
    if not article:
        return redirect('error')

    user = request.user
    like = Article_like.objects.filter(article_like=article, user=user).first()

    if like:
        like.delete()
    else:
        Article_like.objects.create(article_like=article, user=user)
    return redirect('article_detail', article_id=article_id)
  
def go_to_login(request):   
    return render(request, 'login_required.html')

def base(request):   
    return render(request, 'base.html')

def about1(request):   
    return render(request, 'about1.html')

def search_article(request):
    if request.method == 'POST':
        article = request.POST['makala']
        articles = Article.objects.filter(title__icontains=article)
        categories = ArticleCategory.objects.all()
        context = {'article_list': articles, 'categories': categories}
        return render(request, 'article.html', context)

def article_detail(request, article_id):
    article = Article.objects.filter(id=article_id).first()
    if not article:
        raise Http404("Статья не найдена")

    if hasattr(article, 'increment_read'):
        article.increment_read()

    if request.user.is_authenticated:
        read_record, created = Article_read.objects.get_or_create(user=request.user, article_read=article)
        read_articles_count = Article_read.objects.filter(user=request.user).count()
        is_liked = Article_like.objects.filter(article_like=article, user=request.user).exists()
    else:
        read_articles_count = 0
        is_liked = False

    article_comments = Article_comment.objects.filter(article_comment__id=article_id)
    context = {
        'article': article,
        'article_id': article_id,
        'article_comments': article_comments,
        'read_articles_count': read_articles_count,
        'is_liked': is_liked
    }
    return render(request, 'article_detail.html', context)

@login_required
def article_comment(request, article_id):
    if request.method == 'POST':
        article = Article.objects.filter(id=article_id).first()
        user = request.user
        comment = request.POST['comment']
        Article_comment.objects.create(article_comment=article, user=user, comment=comment)
    return redirect('article_detail', article_id=article_id)

def is_admin(user):
    return user.is_staff or user.is_superuser

# Функции для категоризации PDF-файлов
def extract_doi_from_pdf(pdf_path):
    """Извлекает DOI из PDF-файла с помощью PyMuPDF."""
    doc = None
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text()
            if text:
                doi_pattern = r"10\.[0-9]{4,9}/[^\s]+"
                doi_match = re.search(doi_pattern, text)
                if doi_match:
                    return doi_match.group(0)
        return None
    except Exception as e:
        logger.error(f"Ошибка извлечения DOI из {pdf_path}: {e}")
        return None
    finally:
        if doc is not None and not doc.is_closed:
            try:
                doc.close()
                logger.debug(f"Файл {pdf_path} закрыт")
            except Exception as e:
                logger.error(f"Ошибка закрытия файла {pdf_path}: {e}")

def get_category_by_doi(doi):
    """Получает категорию из метаданных CrossRef по DOI."""
    works = Works()
    try:
        metadata = works.doi(doi)
        if metadata and "subject" in metadata:
            subjects = metadata["subject"]
            for subject in subjects:
                subject = subject.lower()
                if "education" in subject:
                    return "Education"
                if "iot" in subject or "internet of things" in subject:
                    return "IoT"
                if "cybersecurity" in subject or "security" in subject:
                    return "Cybersecurity"
                if "cryptography" in subject or "crypto" in subject:
                    return "Cryptography"
                if "mathematic" in subject:
                    return "Mathematics"
                if "sport" in subject or "athletic" in subject:
                    return "Sport"
                if "turkmenistan" in subject:
                    return "Turkmenistan"
                if "medicine" in subject:
                    return "Medicine"
            return subjects[0] if subjects else "Unknown"
        return "Unknown"
    except Exception as e:
        logger.error(f"Ошибка при запросе метаданных для DOI {doi}: {e}")
        return "Unknown"

def get_category_by_filename(filename):
    """Определяет категорию по ключевым словам в имени файла."""
    categories = {
        "Education": [
            "education", "educational", "learning", "teaching", "pedagogy", "instruction",
            "curriculum", "classroom", "school", "student", "teacher", "academic",
            "primary education", "secondary education", "higher education", "tertiary education",
            "university", "college", "vocational education", "distance education", "online learning",
            "educational technology", "e-learning", "curriculum development", "assessment and evaluation",
            "educational policy", "inclusive education", "STEM education", "early childhood education",
            "adult education", "teacher training", "lifelong learning", "bilim", "mekdep", "mektep"
        ],
        "IoT": [
            "internet of things", "iot", "smart device", "smart devices", "sensor", "sensors",
            "connected device", "connected devices", "embedded systems", "wireless sensor networks",
            "machine-to-machine", "M2M", "edge computing", "fog computing", "smart home", "smart city",
            "industrial iot", "IIoT", "wearable devices", "real-time monitoring", "remote sensing",
            "actuator", "data acquisition", "IoT architecture", "IoT platform", "IoT application"
        ],
        "Cybersecurity": [
            "cybersecurity", "security", "cyber", "cyber attack", "cyber threat", "cyber defense",
            "attack", "defense", "hacking", "ethical hacking", "penetration testing", "malware",
            "phishing", "ransomware", "firewall", "encryption", "decryption", "information security",
            "network security", "software security", "hardware security", "computing", "secure computing",
            "information technology", "data protection", "data breach", "access control", "identity management",
            "authentication", "authorization", "digital forensics", "threat detection", "intrusion detection",
            "intrusion prevention", "vulnerability", "risk assessment", "tehnologiýa"
        ],
        "Cryptography": [
            "cryptography", "crypto", "encryption", "decryption", "cipher", "ciphertext", "plaintext",
            "cryptanalysis", "cryptographic algorithm", "symmetric encryption", "asymmetric encryption",
            "public key", "private key", "key exchange", "digital signature", "hash function", "secure hash",
            "SHA", "AES", "RSA", "block cipher", "stream cipher", "elliptic curve cryptography", "ECC",
            "post-quantum cryptography", "homomorphic encryption", "zero-knowledge proof", "quantum cryptography",
            "key management", "PKI", "TLS", "SSL"
        ],
        "Mathematics": [
            "mathematics", "math", "algebra", "linear algebra", "abstract algebra", "geometry",
            "euclidean geometry", "non-euclidean geometry", "analytic geometry", "calculus",
            "differential calculus", "integral calculus", "multivariable calculus", "statistics",
            "statistic", "probability", "probability theory", "number theory", "discrete mathematics",
            "combinatorics", "topology", "set theory", "logic", "mathematical logic", "graph theory",
            "mathematical modeling", "numerical methods", "optimization", "differential equations",
            "partial differential equations", "game theory", "mathematical analysis", "functional analysis",
            "fuzzy logic"
        ],
        "Sport": [
            "sport", "sports", "athletics", "physical activity", "fitness", "exercise", "training",
            "coaching", "competition", "tournament", "match", "game", "team sport", "individual sport",
            "endurance", "strength training", "cardio", "aerobic exercise", "anaerobic exercise",
            "performance analysis", "sports science", "sports medicine", "injury prevention", "recovery",
            "physical education", "athlete", "coach", "yaryş", "çempionat", "olympics", "paralympics",
            "e-sports", "sports psychology", "sports nutrition", "sport physiology"
        ],
        "Turkmenistan": [
            "turkmenistan", "türkmenistan", "turkmen", "türkmen", "ashgabat", " Aşgabat", "central asia",
            "central asian", "turkmen culture", "turkmen language", "turkmen history", "kara kum",
            "caspian sea", "silk road", "post-soviet states", "turkmen traditions", "turkmen carpet",
            "oguz", "turkmen diaspora"
        ],
        "Medicine": [
            "medicine", "medical", "health", "healthcare", "syndrome", "disease", "disorder",
            "diagnosis", "treatment", "therapy", "clinical", "patient", "doctor", "nurse", "hospital",
            "scientific", "science", "medical research", "clinical research", "experiment", "biomedical",
            "biology", "human biology", "anatomy", "physiology", "genetics", "immunology", "pathology",
            "epidemiology", "pharmacology", "neuroscience", "public health", "mental health", "physics",
            "medical physics", "chemistry", "biochemistry", "ylmy", "serotonin", "transporter", "gene",
            "bipolar", "autistic", "psychoses", "tourette", "compulsive", "genetic", "population",
            "structural", "mutational", "microsomal"
        ]
    }
    name = filename.lower().replace(".pdf", "").replace("_", " ")
    for category, keywords in categories.items():
        if any(keyword in name for keyword in keywords):
            return category
    return "Unknown"

def create_category_folders(base_dir, categories):
    """Создаёт папки для категорий, если они не существуют."""
    for category in categories + ["Unknown"]:
        folder_path = os.path.join(base_dir, category)
        os.makedirs(folder_path, exist_ok=True)

def log_categorization(filename, category, doi=None, log_file_path=None):
    """Логирует результаты категоризации в CSV-файл."""
    with open(log_file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([filename, category, doi if doi else "N/A"])

def categorize_pdf_files(temp_dir, files):
    """Категоризирует PDF-файлы и перемещает их в соответствующие папки."""
    logger.debug(f"Начало категоризации в папке: {temp_dir}")
    categories = [
        "Education", "IoT", "Cybersecurity", "Cryptography",
        "Mathematics", "Sport", "Medicine", "Turkmenistan"
    ]
    
    # Создаём папки в выбранной директории
    create_category_folders(temp_dir, categories)
    logger.debug(f"Созданы папки категорий: {categories + ['Unknown']}")
    
    # Создаём CSV-файл для лога
    log_file_path = os.path.join(temp_dir, "categorization_log.csv")
    if not os.path.exists(log_file_path):
        with open(log_file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Filename", "Category", "DOI"])
    logger.debug(f"Создан лог-файл: {log_file_path}")

    category_counts = {cat: 0 for cat in categories + ["Unknown"]}
    total_files = 0
    skipped_files = 0
    categorized_files = []

    for file in files:
        total_files += 1
        file_path = os.path.join(temp_dir, file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # Извлекаем DOI
        doi = extract_doi_from_pdf(file_path)
        if doi:
            category = get_category_by_doi(doi)
            if category != "Unknown":
                logger.debug(f"Категория по DOI: {category}")
            else:
                category = get_category_by_filename(file.name)
        else:
            category = get_category_by_filename(file.name)
        logger.debug(f"Определена категория для {file.name}: {category}")

        # Логируем результат
        log_categorization(file.name, category, doi, log_file_path)
        categorized_files.append((file.name, category))

        # Определяем целевую папку
        category_folder = os.path.join(temp_dir, category)
        new_filepath = os.path.join(category_folder, file.name)

        # Перемещаем файл
        try:
            shutil.move(file_path, new_filepath)
            category_counts[category] += 1
            logger.debug(f"Файл перемещён: {file.name} в {category}")
        except Exception as e:
            logger.error(f"Ошибка при перемещении {file.name}: {e}")
            skipped_files += 1
            categorized_files.append((file.name, f"Ошибка: {str(e)}"))

    logger.debug(f"Завершена категоризация. Обработано: {total_files}, Пропущено: {skipped_files}")
    return {
        "total_files": total_files,
        "skipped_files": skipped_files,
        "category_counts": category_counts,
        "categorized_files": categorized_files,
        "output_dir": temp_dir
    }

def sanitize_filename(filename):
    """Очищает имя файла от недопустимых символов."""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.replace(' ', '_')
    filename = filename[:100]
    return filename

def extract_title_from_pdf(pdf_path):
    """Извлекает заголовок из PDF-файла для переименования, с использованием OCR при необходимости."""
    doc = None
    try:
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        title = metadata.get('title', '').strip()
        if title and len(title) > 5:
            return title

        page = doc[0]
        text = page.get_text("text").strip()
        if text:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 10:
                    return line

        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        ocr_text = pytesseract.image_to_string(img, lang="eng")
        if ocr_text:
            lines = ocr_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 10:
                    return line
        return None
    except Exception as e:
        logger.error(f"Ошибка извлечения заголовка из {pdf_path}: {e}")
        return None
    finally:
        if doc is not None and not doc.is_closed:
            try:
                doc.close()
                logger.debug(f"Файл {pdf_path} закрыт")
            except Exception as e:
                logger.error(f"Ошибка закрытия файла {pdf_path}: {e}")

@login_required
@user_passes_test(is_admin)
def admin_advantages(request):
    categories = ArticleCategory.objects.all()

    if request.method == 'POST':
        logger.debug(f"Получен POST-запрос: {request.POST}")

        # Обработка добавления статей
        if 'add_articles' in request.POST:
            logger.debug("Обработка добавления статей")
            category_id = request.POST.get('category')
            files = request.FILES.getlist('files')

            if not category_id or not files:
                request.session['notification'] = {
                    'type': 'error',
                    'message': 'Выберите категорию и файлы для загрузки'
                }
                return HttpResponseRedirect(reverse('admin_advantages'))

            try:
                category = ArticleCategory.objects.get(id=category_id)
            except ArticleCategory.DoesNotExist:
                request.session['notification'] = {
                    'type': 'error',
                    'message': 'Выбранная категория не существует'
                }
                return HttpResponseRedirect(reverse('admin_advantages'))

            try:
                for file in files:
                    # Проверяем, что файл является PDF
                    mime_type, _ = mimetypes.guess_type(file.name)
                    if mime_type != 'application/pdf':
                        request.session['notification'] = {
                            'type': 'error',
                            'message': f'Файл {file.name} не является PDF'
                        }
                        return HttpResponseRedirect(reverse('admin_advantages'))

                    article = Article(
                        title=file.name,
                        file=file,
                        category=category,
                        user_name=request.user.username
                    )
                    article.save()
                    logger.debug(f"Статья сохранена: {file.name} в {article.file.path}")

                request.session['notification'] = {
                    'type': 'success',
                    'message': f'Добавлено {len(files)} статей'
                }
            except Exception as e:
                logger.error(f"Ошибка при добавлении статей: {e}")
                request.session['notification'] = {
                    'type': 'error',
                    'message': f'Ошибка при добавлении статей: {str(e)}'
                }
            return HttpResponseRedirect(reverse('admin_advantages'))

        # Обработка категоризации файлов
        elif 'categorize_files' in request.POST:
            logger.debug("Обработка категоризации файлов")
            files = request.FILES.getlist('categorize_files')

            if not files:
                request.session['notification'] = {
                    'type': 'error',
                    'message': 'Выберите файлы для категоризации'
                }
                return HttpResponseRedirect(reverse('admin_advantages'))

            temp_dir = tempfile.mkdtemp()
            try:
                # Категоризируем файлы
                result = categorize_pdf_files(temp_dir, files)
                categorized_files = result['categorized_files']
                output_dir = result['output_dir']

                # Создаем ZIP-файл в MEDIA_ROOT
                zip_filename = f"categorized_files_{uuid.uuid4()}.zip"
                zip_path = os.path.join(settings.MEDIA_ROOT, 'zips', zip_filename)
                os.makedirs(os.path.dirname(zip_path), exist_ok=True)

                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(output_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, output_dir)
                            zipf.write(file_path, arcname)

                if os.path.exists(zip_path):
                    logger.debug(f"ZIP-файл создан: {zip_path}")
                else:
                    logger.error(f"ZIP-файл не создан: {zip_path}")

                # Сохраняем относительный путь в сессии
                request.session['download_file'] = os.path.join('zips', zip_filename)
                request.session['notification'] = {
                    'type': 'success',
                    'message': f'Категоризировано {result["total_files"] - result["skipped_files"]} из {result["total_files"]} файлов'
                }
            except Exception as e:
                logger.error(f"Ошибка при категоризации файлов: {e}")
                request.session['notification'] = {
                    'type': 'error',
                    'message': f'Ошибка при категоризации файлов: {str(e)}'
                }
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"Временная директория {temp_dir} удалена")
            return HttpResponseRedirect(reverse('admin_advantages'))

        # Обработка переименования файлов
        elif 'rename_files' in request.POST:
            logger.debug("Обработка переименования файлов")
            files = request.FILES.getlist('rename_files')

            if not files:
                request.session['notification'] = {
                    'type': 'error',
                    'message': 'Выберите файлы для переименования'
                }
                return HttpResponseRedirect(reverse('admin_advantages'))

            temp_dir = tempfile.mkdtemp()
            log_file_path = os.path.join(temp_dir, 'rename_log.csv')

            try:
                renamed_files = []
                with open(log_file_path, 'w', newline='', encoding='utf-8') as log_file:
                    writer = csv.writer(log_file)
                    writer.writerow(['Original Name', 'New Name'])

                    for file in files:
                        # Проверяем, что файл является PDF
                        mime_type, _ = mimetypes.guess_type(file.name)
                        if mime_type != 'application/pdf':
                            writer.writerow([file.name, 'Не переименован: не PDF'])
                            continue

                        file_path = os.path.join(temp_dir, file.name)
                        with open(file_path, 'wb+') as destination:
                            for chunk in file.chunks():
                                destination.write(chunk)

                        new_name = file.name
                        try:
                            # Пробуем извлечь заголовок
                            title = extract_title_from_pdf(file_path)
                            if title:
                                new_name = sanitize_filename(title) + '.pdf'
                        except Exception as e:
                            logger.warning(f"Не удалось извлечь заголовок для {file.name}: {e}")

                        new_file_path = os.path.join(temp_dir, new_name)
                        if new_name != file.name:
                            shutil.move(file_path, new_file_path)
                            renamed_files.append((file.name, new_name))
                            writer.writerow([file.name, new_name])
                            logger.debug(f"Файл {file.name} переименован в {new_name}")
                        else:
                            writer.writerow([file.name, 'Не переименован'])
                            logger.debug(f"Файл {file.name} не переименован")

                # Создаем ZIP-файл в MEDIA_ROOT
                zip_filename = f"renamed_files_{uuid.uuid4()}.zip"
                zip_path = os.path.join(settings.MEDIA_ROOT, 'zips', zip_filename)
                os.makedirs(os.path.dirname(zip_path), exist_ok=True)

                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for _, new_filename in renamed_files:
                        file_path = os.path.join(temp_dir, new_filename)
                        zipf.write(file_path, new_filename)
                    zipf.write(log_file_path, "rename_log.csv")

                if os.path.exists(zip_path):
                    logger.debug(f"ZIP-файл создан: {zip_path}")
                else:
                    logger.error(f"ZIP-файл не создан: {zip_path}")

                request.session['download_file'] = os.path.join('zips', zip_filename)
                request.session['notification'] = {
                    'type': 'success',
                    'message': f'Переименовано {len(renamed_files)} из {len(files)} файлов'
                }
            except Exception as e:
                logger.error(f"Ошибка при переименовании файлов: {e}")
                request.session['notification'] = {
                    'type': 'error',
                    'message': f'Ошибка при переименовании файлов: {str(e)}'
                }
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"Временная директория {temp_dir} удалена")
            return HttpResponseRedirect(reverse('admin_advantages'))

    notification = request.session.pop('notification', None)
    download_file = request.session.pop('download_file', None)
    logger.debug(f"Передача в шаблон: notification={notification}, download_file={download_file}")

    return render(request, 'admin_advantages.html', {
        'categories': categories,
        'notification': notification,
        'download_file': download_file
    })

def contact(request):
    if request.method == 'POST':
        title = request.POST['title']
        message = request.POST['message']
        user = request.user
        result = Contact.objects.create(title=title, message=message, user=user)
        if result:
            messages.success(request, 'Habar üçin sagboluň!')
        else:
            messages.error(request, 'Näsazlyk ýüze çykdy.')
        return render(request, 'contact.html')
    return render(request, 'contact.html')

def about(request):
    return render(request, 'about.html')

def profile(request):
    articles = Article.objects.filter(user_name__icontains=request.user.username)
    paginator = Paginator(articles, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = ArticleCategory.objects.all()
    form = ArticleForm()
    context = {'categories': categories, 'form': form, 'page_obj': page_obj}
    return render(request, 'profile.html', context)

@login_required
def add_article(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.user_name = request.user.username
            article.save()
            return redirect('profile')
    else:
        form = ArticleForm()
    return render(request, 'add_article.html', {'form': form})

def register(request):
    from .forms import RegistrationForm  # Импортируем здесь, чтобы избежать циклического импорта
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'Registration successful.')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def download_file(request):
    relative_file_path = request.GET.get('file')
    if not relative_file_path:
        logger.error("Путь к файлу не указан")
        return HttpResponse("Файл не найден", status=404)

    # Формируем полный путь, ограничивая его MEDIA_ROOT
    file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
    
    # Проверяем, что путь находится внутри MEDIA_ROOT
    if not file_path.startswith(settings.MEDIA_ROOT):
        logger.error(f"Попытка доступа к файлу вне MEDIA_ROOT: {file_path}")
        return HttpResponse("Доступ запрещен", status=403)

    if not os.path.exists(file_path):
        logger.error(f"Файл не найден: {file_path}")
        return HttpResponse("Файл не найден", status=404)

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/zip')
        filename = os.path.basename(file_path)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Удаляем файл после скачивания
    try:
        os.remove(file_path)
        logger.debug(f"Файл {file_path} удалён после скачивания")
    except Exception as e:
        logger.error(f"Ошибка удаления файла {file_path}: {e}")

    return response