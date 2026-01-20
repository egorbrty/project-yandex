# parser.py - с задержкой 1 секунда между запросами
import csv
import os
import time
import socket
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from collections import defaultdict
from typing import List, Dict, Tuple

from config import Config

class HabrParser:
    """Парсер реальных данных с Habr с защитой от зависаний"""
    
    @staticmethod
    def normalize_login(s: str) -> str:
        """Нормализует имя пользователя Habr"""
        s = s.strip().replace("https://", "").replace("http://", "")
        s = s.replace("habr.com/", "").replace("www.habr.com/", "")
        s = s.strip("/").lstrip("@")
        return s.split("/")[-1]
    
    @staticmethod
    def add_or_replace_query_param(url: str, key: str, value: str) -> str:
        """Добавляет или заменяет параметр в URL"""
        p = urlparse(url)
        qs = parse_qs(p.query)
        qs[key] = [value]
        return urlunparse((p.scheme, p.netloc, p.path, p.params, 
                          urlencode(qs, doseq=True), p.fragment))
    
    @staticmethod
    def feed_url_candidates(login: str, section: str, lang: str) -> List[str]:
        """Генерирует URL для RSS ленты пользователя Habr"""
        base1 = f"https://habr.com/{lang}/rss/users/{login}/{section}/?fl={lang}"
        base2 = f"https://habr.com/{lang}/rss/users/{login}/publications/{section}/?fl={lang}"
        return [
            HabrParser.add_or_replace_query_param(base1, "limit", str(Config.LIMIT)),
            HabrParser.add_or_replace_query_param(base2, "limit", str(Config.LIMIT)),
        ]
    
    @staticmethod
    def _tag(elem, name: str) -> bool:
        """Проверяет соответствие тега"""
        return elem.tag.lower().endswith(name.lower())
    
    @staticmethod
    def parse_datetime(text: str) -> datetime:
        """Парсит дату из RSS в UTC"""
        if not text:
            return None
        text = text.strip()
        try:
            dt = parsedate_to_datetime(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            try:
                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"
                dt = datetime.fromisoformat(text)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                return None
    
    @staticmethod
    def parse_feed(xml_text: str, section: str) -> List[Dict]:
        """Парсит RSS ленту Habr"""
        if not xml_text.strip():
            return []
        
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return []
        
        posts = []
        
        # Atom формат
        if HabrParser._tag(root, "feed"):
            for entry in root.iter():
                if not HabrParser._tag(entry, "entry"):
                    continue
                
                uid = None
                themes = []
                date_utc = None
                
                for child in entry:
                    if HabrParser._tag(child, "id") or HabrParser._tag(child, "link"):
                        uid = (child.text or "").strip()
                    elif HabrParser._tag(child, "category"):
                        term = (child.attrib.get("term") or "").strip().lower()
                        if term and term not in ["rss", "atom", "habr"]:
                            themes.append(term)
                    elif HabrParser._tag(child, "published") or HabrParser._tag(child, "updated"):
                        dt = HabrParser.parse_datetime(child.text)
                        if dt:
                            date_utc = dt
                
                if uid and date_utc:
                    theme = themes[0] if themes else "other"
                    posts.append({
                        'uid': uid,
                        'date': date_utc,
                        'theme': theme,
                        'section': section
                    })
            return posts
        
        # RSS формат
        for item in root.iter():
            if not HabrParser._tag(item, "item"):
                continue
            
            uid = None
            themes = []
            date_utc = None
            
            for child in item:
                if HabrParser._tag(child, "guid") or HabrParser._tag(child, "link"):
                    uid = (child.text or "").strip()
                elif HabrParser._tag(child, "category") and child.text:
                    theme_text = child.text.strip().lower()
                    if theme_text not in ["rss", "atom", "habr"]:
                        themes.append(theme_text)
                elif HabrParser._tag(child, "pubDate") and child.text:
                    dt = HabrParser.parse_datetime(child.text)
                    if dt:
                        date_utc = dt
            
            if uid and date_utc:
                theme = themes[0] if themes else "other"
                posts.append({
                    'uid': uid,
                    'date': date_utc,
                    'theme': theme,
                    'section': section
                })
        
        return posts
    
    def fetch_url_with_retry(self, url: str, retries: int = Config.MAX_RETRIES) -> str:
        """Выполняет запрос к URL с повторными попытками"""
        for attempt in range(retries):
            try:
                # Добавляем задержку между попытками (кроме первой)
                if attempt > 0:
                    time.sleep(Config.RETRY_DELAY)
                
                # Устанавливаем таймаут сокета
                socket.setdefaulttimeout(Config.TIMEOUT)
                
                # Создаем запрос с заголовками
                req = urllib.request.Request(url, headers=Config.HEADERS)
                
                # Выполняем запрос с ограничением по времени
                with urllib.request.urlopen(req, timeout=Config.TIMEOUT) as response:
                    if response.status != 200:
                        if response.status == 404:
                            return ""  # Пользователь не существует
                        if attempt < retries - 1:
                            continue  # Пробуем снова
                        return ""
                    
                    # Читаем ответ с ограничением размера
                    xml_text = response.read(10 * 1024 * 1024).decode('utf-8')  # Ограничение 10 МБ
                    return xml_text
                    
            except socket.timeout:
                print(f"    Таймаут при попытке {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    continue
                return ""
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return ""  # Пользователь не существует
                print(f"    HTTP ошибка {e.code} при попытке {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    continue
                return ""
            except urllib.error.URLError as e:
                print(f"    Ошибка URL при попытке {attempt + 1}/{retries}: {e.reason}")
                if attempt < retries - 1:
                    continue
                return ""
            except Exception as e:
                print(f"    Общая ошибка при попытке {attempt + 1}/{retries}: {e}")
                if attempt < retries - 1:
                    continue
                return ""
        
        return ""
    
    def fetch_user_publications(self, user_id: str) -> List[Dict]:
        """Получает все публикации пользователя Habr с защитой от зависаний"""
        all_posts = []
        seen_uids = set()  # Для отслеживания уникальных публикаций
        
        for section in Config.SECTIONS:
            for lang in Config.LANGS:
                for url in self.feed_url_candidates(user_id, section, lang):
                    try:
                        # Добавляем задержку между запросами - 1 СЕКУНДА
                        time.sleep(Config.DELAY)
                        
                        xml_text = self.fetch_url_with_retry(url)
                        if not xml_text:
                            continue
                        
                        posts = self.parse_feed(xml_text, section)
                        
                        if posts:
                            # Добавляем только уникальные публикации
                            for post in posts:
                                if post['uid'] and post['uid'] not in seen_uids:
                                    seen_uids.add(post['uid'])
                                    all_posts.append(post)
                            
                            # Если нашли публикации, переходим к следующему разделу
                            break
                        
                    except Exception as e:
                        print(f"    Непредвиденная ошибка при запросе к {url}: {e}")
                        time.sleep(Config.RETRY_DELAY)
                        continue
        
        return all_posts
    
    def collect_data(self, users: List[str]) -> Tuple[List[Dict], Dict[str, int]]:
        """Собирает данные для списка пользователей"""
        all_publications = []
        user_publication_counts = defaultdict(int)
        
        print(f"Начинаем сбор данных для {len(users)} пользователей...")
        print(f"Задержка между запросами: {Config.DELAY} секунд")
        print(f"Таймаут: {Config.TIMEOUT} секунд, Повторные попытки: {Config.MAX_RETRIES}")
        print("Это может занять значительное время...\n")
        
        for idx, raw_login in enumerate(users, 1):
            user_id = self.normalize_login(raw_login)
            
            # Показываем прогресс каждые 10 пользователей или для последнего
            if idx % 10 == 0 or idx == len(users):
                print(f"[{idx}/{len(users)}] Сбор данных для: {user_id}")
            
            try:
                publications = self.fetch_user_publications(user_id)
                
                for pub in publications:
                    pub['user_id'] = user_id
                    all_publications.append(pub)
                
                # Правильно считаем количество уникальных публикаций для пользователя
                user_publication_counts[user_id] = len(publications)
                
                # Показываем количество публикаций только для каждого 10-го пользователя
                if idx % 10 == 0 or idx == len(users):
                    print(f"  Найдено уникальных публикаций: {len(publications)}")
                
                # Сохраняем данные каждые 20 пользователей для безопасности
                if idx % 20 == 0:
                    self._save_partial_data(all_publications, user_publication_counts, idx)
                    print(f"  [Автосохранение] Данные сохранены после {idx} пользователей")
                
            except KeyboardInterrupt:
                print("\n\nПолучен сигнал прерывания (Ctrl+C)")
                print("Сохраняем уже собранные данные...")
                self._save_partial_data(all_publications, user_publication_counts, idx)
                print(f"Сохранено данных для {idx} пользователей")
                raise  # Передаем прерывание дальше
                
            except Exception as e:
                print(f"  Ошибка для {user_id}: {e}")
                # Ждем перед следующим пользователем в случае ошибки
                time.sleep(2)
                continue
        
        return all_publications, dict(user_publication_counts)
    
    def _save_partial_data(self, publications: List[Dict], user_counts: Dict[str, int], current_idx: int) -> None:
        """Сохраняет частичные данные для возможности продолжения"""
        Config.ensure_output_dir()
        
        # Сохраняем публикации
        with open(f"{Config.OUTPUT_DIR}/raw_publications_partial.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "date", "theme", "section", "uid"])
            for pub in publications:
                writer.writerow([
                    pub['user_id'],
                    pub['date'].strftime("%Y-%m-%d"),
                    pub['theme'],
                    pub['section'],
                    pub['uid']
                ])
        
        # Сохраняем счетчики
        with open(f"{Config.OUTPUT_DIR}/raw_user_counts_partial.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "publication_count"])
            for user_id, count in user_counts.items():
                writer.writerow([user_id, count])

def main():
    """Основная функция парсера"""
    Config.ensure_output_dir()
    
    # Загрузка списка пользователей
    try:
        with open(Config.INPUT_FILE, 'r', encoding='utf-8') as f:
            all_users = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Ошибка: Файл {Config.INPUT_FILE} не найден!")
        return
    
    # Проверяем, есть ли уже собранные данные
    processed_users = set()
    if os.path.exists(f"{Config.OUTPUT_DIR}/raw_publications.csv"):
        try:
            with open(f"{Config.OUTPUT_DIR}/raw_publications.csv", "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)  # Пропускаем заголовок
                for row in reader:
                    if row:
                        processed_users.add(row[0])  # user_id
            print(f"Найдены данные для {len(processed_users)} уже обработанных пользователей")
        except:
            pass
    
    # Фильтруем уже обработанных пользователей
    users_to_process = [user for user in all_users if HabrParser.normalize_login(user) not in processed_users]
    
    print(f"Загружено пользователей всего: {len(all_users)}")
    print(f"Уже обработано: {len(processed_users)}")
    print(f"Осталось обработать: {len(users_to_process)}")
    
    if not users_to_process:
        print("Все пользователи уже обработаны!")
        
        # Загружаем существующие данные для подсчета статистики
        all_publications = []
        user_counts = {}
        user_publications = defaultdict(list)
        
        if os.path.exists(f"{Config.OUTPUT_DIR}/raw_publications.csv"):
            with open(f"{Config.OUTPUT_DIR}/raw_publications.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pub_data = {
                        'user_id': row['user_id'],
                        'date': datetime.strptime(row['date'], "%Y-%m-%d"),
                        'theme': row['theme'],
                        'section': row['section'],
                        'uid': row['uid']
                    }
                    all_publications.append(pub_data)
                    user_publications[row['user_id']].append(pub_data)
            
            # Правильно считаем количество публикаций для каждого пользователя
            for user_id, pubs in user_publications.items():
                user_counts[user_id] = len(pubs)
        
        print(f"\nВсего собрано публикаций: {len(all_publications)}")
        print(f"Обработано пользователей: {len(user_counts)}")
        return
    
    # Сбор данных
    parser = HabrParser()
    try:
        publications, user_counts = parser.collect_data(users_to_process)
        
        # Сохранение сырых данных (дописываем в существующий файл)
        mode = "a" if os.path.exists(f"{Config.OUTPUT_DIR}/raw_publications.csv") else "w"
        with open(f"{Config.OUTPUT_DIR}/raw_publications.csv", mode, encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if mode == "w":
                writer.writerow(["user_id", "date", "theme", "section", "uid"])
            for pub in publications:
                writer.writerow([
                    pub['user_id'],
                    pub['date'].strftime("%Y-%m-%d"),
                    pub['theme'],
                    pub['section'],
                    pub['uid']
                ])
        
        # Обновляем счетчики пользователей
        existing_counts = {}
        if os.path.exists(f"{Config.OUTPUT_DIR}/raw_user_counts.csv"):
            with open(f"{Config.OUTPUT_DIR}/raw_user_counts.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_counts[row['user_id']] = int(row['publication_count'])
        
        # Добавляем новые счетчики
        for user_id, count in user_counts.items():
            existing_counts[user_id] = count
        
        # Сохраняем обновленные счетчики
        with open(f"{Config.OUTPUT_DIR}/raw_user_counts.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "publication_count"])
            for user_id, count in existing_counts.items():
                writer.writerow([user_id, count])
        
        print(f"\nСбор данных завершен!")
        print(f"Собрано уникальных публикаций на этой сессии: {len(publications)}")
        print(f"Обработано пользователей на этой сессии: {len(user_counts)}")
        print(f"Всего обработано пользователей: {len(existing_counts)}")
        print(f"Сохранено в {Config.OUTPUT_DIR}/raw_*.csv")
        
        # Удаляем временные файлы
        if os.path.exists(f"{Config.OUTPUT_DIR}/raw_publications_partial.csv"):
            os.remove(f"{Config.OUTPUT_DIR}/raw_publications_partial.csv")
        if os.path.exists(f"{Config.OUTPUT_DIR}/raw_user_counts_partial.csv"):
            os.remove(f"{Config.OUTPUT_DIR}/raw_user_counts_partial.csv")
            
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем.")
        print("Данные сохранены в частичных файлах:")
        print(f"  {Config.OUTPUT_DIR}/raw_publications_partial.csv")
        print(f"  {Config.OUTPUT_DIR}/raw_user_counts_partial.csv")
        print("\nДля продолжения запустите программу снова.")
        return

if __name__ == "__main__":
    main()