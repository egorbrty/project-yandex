# analyzer.py - упрощенная версия без matplotlib и numpy
import csv
import statistics
from collections import Counter
from typing import List, Dict, Tuple

from config import Config

class ActivityAnalyzer:
    """Анализирует активность пользователей и отвечает на вопросы"""
    
    def __init__(self):
        self.publications = []
        self.user_counts = {}
        self.daily_activity = []
        self.themes = []
        
    def load_data(self) -> None:
        """Загружает данные из таблиц"""
        Config.ensure_output_dir()
        
        # Загрузка пользователей
        with open(f"{Config.OUTPUT_DIR}/users.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.user_counts[row['user_id']] = int(row['publication_count'])
        
        # Загрузка ежедневной активности
        with open(f"{Config.OUTPUT_DIR}/daily_activity.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.daily_activity.append({
                    'date': row['date'],
                    'count': int(row['publication_count']),
                    'weekday': row['weekday']
                })
        
        # Загрузка тем
        with open(f"{Config.OUTPUT_DIR}/themes.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.themes.append({
                    'theme': row['theme'],
                    'count': int(row['publication_count']),
                    'unique_users': int(row['unique_users']),
                    'avg_per_user': float(row['avg_per_user'])
                })
    
    def answer_question_1(self) -> Dict:
        """1. Кто самые активные и пассивные пользователи?"""
        sorted_users = sorted(self.user_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Топ-10 активных
        top_active = sorted_users[:10]
        
        # Топ-10 пассивных (с наименьшим количеством публикаций > 0)
        active_users = [(u, c) for u, c in sorted_users if c > 0]
        if len(active_users) >= 10:
            top_passive = active_users[-10:]
        else:
            top_passive = active_users
        
        return {
            'top_active': top_active,
            'top_passive': top_passive,
            'total_users': len(self.user_counts),
            'users_with_publications': len(active_users)
        }
    
    def answer_question_2(self) -> Dict:
        """2. Сколько пользователей проявляют активность? На сколько разнообразен трафик?"""
        publication_counts = list(self.user_counts.values())
        
        if not publication_counts:
            return {}
        
        # Базовые статистики
        total_publications = sum(publication_counts)
        active_users = sum(1 for count in publication_counts if count > 0)
        inactive_users = len(publication_counts) - active_users
        
        # Статистики распределения
        mean = statistics.mean(publication_counts)
        median = statistics.median(publication_counts)
        stdev = statistics.stdev(publication_counts) if len(publication_counts) > 1 else 0
        
        # Коэффициент вариации
        cv = (stdev / mean * 100) if mean > 0 else 0
        
        # Распределение по группам активности
        low_activity = sum(1 for count in publication_counts if count <= 5)
        medium_activity = sum(1 for count in publication_counts if 5 < count <= 20)
        high_activity = sum(1 for count in publication_counts if count > 20)
        
        # Простая оценка разнообразия
        diversity_score = stdev / mean if mean > 0 else 0
        
        return {
            'total_publications': total_publications,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'mean_publications': round(mean, 2),
            'median_publications': median,
            'std_dev': round(stdev, 2),
            'cv_percent': round(cv, 2),
            'diversity_score': round(diversity_score, 3),
            'low_activity': low_activity,
            'medium_activity': medium_activity,
            'high_activity': high_activity
        }
    
    def answer_question_3(self) -> Dict:
        """3. Как изменяется активность по дням/неделям/сезонам?"""
        if not self.daily_activity:
            return {}
        
        # Анализ по дням недели
        weekday_counts = Counter()
        for day in self.daily_activity:
            weekday_counts[day['weekday']] += day['count']
        
        # Самый активный день
        most_active_day = weekday_counts.most_common(1)[0] if weekday_counts else ("", 0)
        
        # Анализ по месяцам
        month_counts = Counter()
        for day in self.daily_activity:
            month = day['date'][:7]  # ГГГГ-ММ
            month_counts[month] += day['count']
        
        # Самый активный месяц
        most_active_month = month_counts.most_common(1)[0] if month_counts else ("", 0)
        
        # Простой анализ тренда
        counts = [day['count'] for day in self.daily_activity]
        if len(counts) > 1:
            first_half = sum(counts[:len(counts)//2])
            second_half = sum(counts[len(counts)//2:])
            if second_half > first_half * 1.1:
                trend = "растёт"
            elif second_half < first_half * 0.9:
                trend = "падает"
            else:
                trend = "стабилен"
        else:
            trend = "недостаточно данных"
        
        return {
            'weekday_distribution': dict(weekday_counts),
            'most_active_day': most_active_day,
            'most_active_month': most_active_month,
            'trend': trend,
            'total_days': len(self.daily_activity),
            'avg_daily_publications': round(sum(counts) / len(counts), 2) if counts else 0
        }
    
    def answer_question_4(self) -> Dict:
        """4. Есть ли зависимость между типом контента и активностью?"""
        if not self.themes:
            return {}
        
        # Самые популярные темы
        sorted_themes = sorted(self.themes, key=lambda x: x['count'], reverse=True)
        top_themes = sorted_themes[:10]
        
        # Концентрация по темам
        total_publications = sum(theme['count'] for theme in self.themes)
        if total_publications > 0:
            top_3_percentage = sum(theme['count'] for theme in sorted_themes[:3]) / total_publications * 100
            top_5_percentage = sum(theme['count'] for theme in sorted_themes[:5]) / total_publications * 100
        else:
            top_3_percentage = top_5_percentage = 0
        
        # Среднее количество публикаций на тему
        avg_publications_per_theme = statistics.mean([t['count'] for t in self.themes]) if self.themes else 0
        
        # Анализ специализации
        if avg_publications_per_theme > 50:
            concentration = "высокая"
        elif avg_publications_per_theme > 20:
            concentration = "умеренная"
        else:
            concentration = "низкая"
        
        return {
            'top_themes': top_themes,
            'total_themes': len(self.themes),
            'top_3_percentage': round(top_3_percentage, 2),
            'top_5_percentage': round(top_5_percentage, 2),
            'avg_publications_per_theme': round(avg_publications_per_theme, 2),
            'concentration': concentration,
            'most_popular_theme': sorted_themes[0] if sorted_themes else None
        }
    
    def generate_report(self) -> None:
        """Генерирует полный отчет с ответами на все вопросы"""
        print("=" * 70)
        print("АНАЛИТИЧЕСКИЙ ОТЧЕТ: АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ HABR")
        print("=" * 70)
        
        # Загрузка данных
        print("\nЗагрузка данных...")
        try:
            self.load_data()
        except FileNotFoundError:
            print("Ошибка: Не найдены файлы данных. Сначала запустите сбор и построение таблиц.")
            return
        
        # Ответ на вопрос 1
        print("\n" + "=" * 70)
        print("1. КТО САМЫЕ АКТИВНЫЕ И ПАССИВНЫЕ ПОЛЬЗОВАТЕЛЕЙ?")
        print("=" * 70)
        answer1 = self.answer_question_1()
        
        print(f"Всего пользователей: {answer1['total_users']}")
        print(f"Пользователей с публикациями: {answer1['users_with_publications']}")
        
        print("\nТОП-10 самых активных пользователей:")
        for i, (user, count) in enumerate(answer1['top_active'], 1):
            print(f"{i:2}. {user:30} - {count:4} публикаций")
        
        print("\nТОП-10 самых пассивных пользователей (с публикациями):")
        for i, (user, count) in enumerate(answer1['top_passive'], 1):
            print(f"{i:2}. {user:30} - {count:4} публикаций")
        
        # Ответ на вопрос 2
        print("\n" + "=" * 70)
        print("2. СКОЛЬКО ПОЛЬЗОВАТЕЛЕЙ ПРОЯВЛЯЮТ АКТИВНОСТЬ?")
        print("   НА СКОЛЬКО РАЗНООБРАЗЕН ПОЛЬЗОВАТЕЛЬСКИЙ ТРАФИК?")
        print("=" * 70)
        answer2 = self.answer_question_2()
        
        print(f"Всего публикаций: {answer2['total_publications']}")
        print(f"Активных пользователей: {answer2['active_users']}")
        print(f"Неактивных пользователей: {answer2['inactive_users']}")
        print(f"\nСтатистика распределения:")
        print(f"  • Среднее: {answer2['mean_publications']:.1f} публикаций на пользователя")
        print(f"  • Медиана: {answer2['median_publications']} публикаций")
        print(f"  • Стандартное отклонение: {answer2['std_dev']:.2f}")
        print(f"  • Коэффициент вариации: {answer2['cv_percent']:.1f}%")
        
        cv = answer2['cv_percent']
        if cv < 50:
            print("  → Низкая вариативность: активность распределена равномерно")
        elif cv < 100:
            print("  → Умеренная вариативность: есть различия в активности")
        else:
            print("  → Высокая вариативность: большие различия между пользователями")
        
        print(f"\nОценка разнообразия трафика: {answer2['diversity_score']:.3f}")
        if answer2['diversity_score'] < 0.5:
            print("  → Низкое разнообразие: пользователи ведут себя схожим образом")
        elif answer2['diversity_score'] < 1.0:
            print("  → Среднее разнообразие: есть разные модели поведения")
        else:
            print("  → Высокое разнообразие: пользователи сильно различаются по активности")
        
        print(f"\nГруппы активности:")
        print(f"  • Низкая активность (≤5 публикаций): {answer2['low_activity']} пользователей")
        print(f"  • Средняя активность (6-20 публикаций): {answer2['medium_activity']} пользователей")
        print(f"  • Высокая активность (>20 публикаций): {answer2['high_activity']} пользователей")
        
        # Ответ на вопрос 3
        print("\n" + "=" * 70)
        print("3. КАК ИЗМЕНЯЕТСЯ АКТИВНОСТЬ ПО ВРЕМЕНИ?")
        print("=" * 70)
        answer3 = self.answer_question_3()
        
        print(f"Общий тренд: активность {answer3['trend']}")
        print(f"Всего дней с активностью: {answer3['total_days']}")
        print(f"Среднедневное количество публикаций: {answer3['avg_daily_publications']:.1f}")
        
        most_active_day, day_count = answer3['most_active_day']
        print(f"\nСамый активный день недели: {most_active_day} ({day_count} публикаций)")
        
        print("\nРаспределение по дням недели:")
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        total = sum(answer3['weekday_distribution'].values())
        
        for day in weekday_order:
            if day in answer3['weekday_distribution']:
                count = answer3['weekday_distribution'][day]
                percentage = (count / total * 100) if total > 0 else 0
                print(f"  • {day:15}: {count:4} публикаций ({percentage:5.1f}%)")
        
        # Ответ на вопрос 4
        print("\n" + "=" * 70)
        print("4. ЕСТЬ ЛИ ЗАВИСИМОСТЬ МЕЖДУ ТИПОМ КОНТЕНТА И АКТИВНОСТЬЮ?")
        print("=" * 70)
        answer4 = self.answer_question_4()
        
        print(f"Всего уникальных тем: {answer4['total_themes']}")
        print(f"Среднее публикаций на тему: {answer4['avg_publications_per_theme']:.1f}")
        print(f"Концентрация тем: {answer4['concentration']}")
        print(f"  • {answer4['top_3_percentage']:.1f}% публикаций в топ-3 темах")
        print(f"  • {answer4['top_5_percentage']:.1f}% публикаций в топ-5 темах")
        
        if answer4['most_popular_theme']:
            theme = answer4['most_popular_theme']
            print(f"\nСамая популярная тема: {theme['theme']}")
            print(f"  • Публикаций: {theme['count']}")
            print(f"  • Уникальных авторов: {theme['unique_users']}")
            print(f"  • Среднее на автора: {theme['avg_per_user']:.1f}")
        
        print("\nТОП-10 самых популярных тем:")
        for i, theme in enumerate(answer4['top_themes'], 1):
            print(f"{i:2}. {theme['theme']:30} - {theme['count']:4} публикаций")
        
        # Выводы
        print("\n" + "=" * 70)
        print("ОСНОВНЫЕ ВЫВОДЫ:")
        print("=" * 70)
        
        # Вывод по концентрации
        if answer4['top_3_percentage'] > 50:
            print("• ВЫСОКАЯ КОНЦЕНТРАЦИЯ ПО ТЕМАМ: Несколько тем доминируют")
        elif answer4['top_3_percentage'] > 30:
            print("• УМЕРЕННАЯ КОНЦЕНТРАЦИЯ: Есть популярные темы, но много разнообразия")
        else:
            print("• НИЗКАЯ КОНЦЕНТРАЦИЯ: Темы распределены равномерно")
        
        # Вывод по активности
        if answer2['cv_percent'] > 100:
            print("• ВЫСОКОЕ НЕРАВЕНСТВО: Небольшая группа пользователей создает большинство контента")
        elif answer2['cv_percent'] > 50:
            print("• УМЕРЕННОЕ НЕРАВЕНСТВО: Есть лидеры, но много активных участников")
        else:
            print("• РАВНОМЕРНОЕ РАСПРЕДЕЛЕНИЕ: Пользователи публикуют примерно одинаково")
        
        # Рекомендации
        print("\nРЕКОМЕНДАЦИИ:")
        print("1. Сфокусироваться на развитии топ-20% самых активных пользователей")
        print("2. Развивать разнообразие тем для привлечения большего числа пользователей")
        print(f"3. Планировать активность на {most_active_day} (самый активный день)")
        print("4. Мотивировать пассивных пользователей к созданию контента")

def main():
    """Основная функция анализа"""
    analyzer = ActivityAnalyzer()
    analyzer.generate_report()

if __name__ == "__main__":
    main()