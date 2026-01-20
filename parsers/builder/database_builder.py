# database_builder.py - исправленная версия
import csv
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Dict, Tuple

from config import Config

class DatabaseBuilder:
    """Строит таблицы для импорта в DataLens"""
    
    @staticmethod
    def load_raw_data() -> Tuple[List[Dict], Dict[str, int]]:
        """Загружает сырые данные"""
        publications = []
        user_counts = {}
        
        try:
            # Загрузка публикаций
            with open(f"{Config.OUTPUT_DIR}/raw_publications.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    publications.append({
                        'user_id': row['user_id'],
                        'date': datetime.strptime(row['date'], "%Y-%m-%d"),
                        'theme': row['theme'],
                        'section': row['section'],
                        'uid': row['uid']
                    })
            
            # Загрузка счетчиков пользователей
            with open(f"{Config.OUTPUT_DIR}/raw_user_counts.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    user_counts[row['user_id']] = int(row['publication_count'])
                    
        except FileNotFoundError:
            print("Ошибка: Сначала запустите parser.py для сбора данных")
            raise
        
        return publications, user_counts
    
    def build_tables(self) -> None:
        """Строит все таблицы для анализа"""
        Config.ensure_output_dir()
        
        print("Загрузка сырых данных...")
        publications, user_counts = self.load_raw_data()
        
        if not publications:
            print("Нет данных для анализа")
            return
        
        print(f"Загружено публикаций: {len(publications)}")
        print(f"Загружено пользователей: {len(user_counts)}")
        
        # Проверяем согласованность данных
        actual_counts = {}
        user_publications = defaultdict(list)
        
        for pub in publications:
            user_publications[pub['user_id']].append(pub)
        
        for user_id, pubs in user_publications.items():
            actual_counts[user_id] = len(pubs)
        
        # Сравниваем с сохраненными счетчиками
        mismatches = 0
        for user_id, actual_count in actual_counts.items():
            saved_count = user_counts.get(user_id, 0)
            if actual_count != saved_count:
                mismatches += 1
                print(f"  Несоответствие для {user_id}: сохранено {saved_count}, фактически {actual_count}")
        
        if mismatches > 0:
            print(f"Найдено несоответствий: {mismatches}")
            print("Используем фактические значения...")
            user_counts = actual_counts
        
        # 1. Таблица публикаций (основная)
        print("Создание таблицы 1: Публикации...")
        sorted_pubs = sorted(publications, key=lambda x: x['date'])
        
        with open(f"{Config.OUTPUT_DIR}/publications.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "user_id", "theme", "section"])
            
            for pub in sorted_pubs:
                writer.writerow([
                    pub['date'].strftime("%Y-%m-%d"),
                    pub['user_id'],
                    pub['theme'],
                    pub['section']
                ])
        
        # 2. Таблица пользователей (агрегированная)
        print("Создание таблицы 2: Пользователи...")
        # Сортировка по количеству публикаций (убывание)
        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
        
        with open(f"{Config.OUTPUT_DIR}/users.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "publication_count", "rank"])
            
            for rank, (user_id, count) in enumerate(sorted_users, 1):
                writer.writerow([user_id, count, rank])
        
        # 3. Таблица ежедневной активности
        print("Создание таблицы 3: Ежедневная активность...")
        daily_counts = Counter()
        
        for pub in publications:
            date_str = pub['date'].strftime("%Y-%m-%d")
            daily_counts[date_str] += 1
        
        # Сортировка по дате
        sorted_dates = sorted(daily_counts.items())
        
        with open(f"{Config.OUTPUT_DIR}/daily_activity.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "publication_count", "weekday"])
            
            for date_str, count in sorted_dates:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                weekday = date_obj.strftime("%A")
                writer.writerow([date_str, count, weekday])
        
        # 4. Таблица по темам
        print("Создание таблица 4: Темы...")
        theme_counts = Counter()
        theme_users = defaultdict(set)
        
        for pub in publications:
            theme_counts[pub['theme']] += 1
            theme_users[pub['theme']].add(pub['user_id'])
        
        # Сортировка по популярности (убывание)
        sorted_themes = theme_counts.most_common()
        
        with open(f"{Config.OUTPUT_DIR}/themes.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["theme", "publication_count", "unique_users", "avg_per_user"])
            
            for theme, count in sorted_themes:
                unique_users = len(theme_users[theme])
                avg_per_user = round(count / unique_users, 2) if unique_users > 0 else 0
                writer.writerow([theme, count, unique_users, avg_per_user])
        
        print("\nТаблицы созданы в папке:", Config.OUTPUT_DIR)
        print(f"Всего пользователей: {len(user_counts)}")
        print(f"Всего публикаций: {len(publications)}")
        
        # Статистика
        if user_counts:
            counts = list(user_counts.values())
            max_count = max(counts)
            min_count = min(counts)
            avg_count = sum(counts) / len(counts)
            
            print(f"\nСтатистика публикаций:")
            print(f"  Максимум: {max_count} публикаций")
            print(f"  Минимум: {min_count} публикаций")
            print(f"  Среднее: {avg_count:.1f} публикаций на пользователя")

def main():
    """Основная функция сборки базы данных"""
    builder = DatabaseBuilder()
    builder.build_tables()

if __name__ == "__main__":
    main()