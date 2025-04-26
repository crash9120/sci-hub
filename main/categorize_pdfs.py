import os
import re
import shutil
import csv
import pdfplumber
from crossref.restful import Works
import warnings

# Отключаем предупреждения CropBox
warnings.filterwarnings("ignore", category=UserWarning, module="pdfplumber")

def extract_doi_from_pdf(pdf_path):
    """Извлекает DOI из PDF-файла."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    doi_pattern = r"10\.[0-9]{4,9}/[^\s]+"
                    doi_match = re.search(doi_pattern, text)
                    if doi_match:
                        return doi_match.group(0)
        return None
    except Exception as e:
        print(f"Ошибка при извлечении DOI из {pdf_path}: {e}")
        return None

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
        print(f"Ошибка при запросе метаданных для DOI {doi}: {e}")
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
            "medical physics", "chemistry", "biochemistry", "ylmy"
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

def log_categorization(filename, new_filename, category, doi=None):
    """Логирует результаты категоризации в CSV-файл."""
    with open("categorization_log.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([filename, new_filename, category, doi if doi else "N/A"])

def categorize_and_move_pdf_files(temp_dir, output_dir):
    """Категоризирует PDF-файлы, переименовывает их и перемещает в соответствующие папки."""
    # Список категорий
    categories = [
        "Education", "IoT", "Cybersecurity", "Cryptography",
        "Mathematics", "Sport", "Medicine", "Turkmenistan"
    ]
    
    # Создаём папки в выходной директории
    create_category_folders(output_dir, categories)
    
    # Создаём CSV-файл для лога, если он не существует
    if not os.path.exists("categorization_log.csv"):
        with open("categorization_log.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Original Filename", "New Filename", "Category", "DOI"])

    # Счётчики для результатов
    category_counts = {cat: 0 for cat in categories + ["Unknown"]}
    total_files = 0
    skipped_files = 0

    for filename in os.listdir(temp_dir):
        if filename.lower().endswith(".pdf"):
            total_files += 1
            pdf_path = os.path.join(temp_dir, filename)
            print(f"Обработка файла: {filename}")

            # Извлекаем DOI
            doi = extract_doi_from_pdf(pdf_path)
            if doi:
                category = get_category_by_doi(doi)
                if category != "Unknown":
                    print(f"Категория по DOI: {category}")
                else:
                    category = get_category_by_filename(filename)
            else:
                category = get_category_by_filename(filename)

            # Переименовываем файл: добавляем категорию и порядковый номер
            base_name = os.path.splitext(filename)[0]
            file_count = category_counts[category] + 1
            new_filename = f"{category}_{file_count}_{base_name}.pdf"
            
            # Логируем результат
            log_categorization(filename, new_filename, category, doi)

            # Определяем целевую папку
            category_folder = os.path.join(output_dir, category)
            new_filepath = os.path.join(category_folder, new_filename)

            # Перемещаем файл
            try:
                shutil.move(pdf_path, new_filepath)
                category_counts[category] += 1
                print(f"Файл перемещён и переименован: {filename} -> {new_filename} в {category}")
            except Exception as e:
                print(f"Ошибка при перемещении {filename}: {e}")
                skipped_files += 1

    return {
        "total_files": total_files,
        "skipped_files": skipped_files,
        "category_counts": category_counts
    }