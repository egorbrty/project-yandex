# config.py
import os

class Config:
    """Конфигурация проекта"""
    INPUT_FILE = 'usernames.txt'
    OUTPUT_DIR = "results"
    
    # Настройки парсера Habr
    LIMIT = 100  # Максимальное количество постов для запроса
    LANGS = ["ru", "en"]
    SECTIONS = ["articles", "posts", "news"]
    
    # Задержка между запросами (в секундах)
    DELAY = 1.0  # Вернули 1 секунду
    
    # Таймауты и повторные попытки
    TIMEOUT = 30  # Таймаут соединения
    MAX_RETRIES = 3  # Максимальное количество попыток
    RETRY_DELAY = 5  # Задержка между повторными попытками
    
    # Headers для запросов
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/atom+xml, text/xml, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    @classmethod
    def ensure_output_dir(cls):
        """Создает директорию для результатов"""
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)