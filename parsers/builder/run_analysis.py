#!/usr/bin/env python3
"""
Главный управляющий скрипт для анализа активности пользователей Habr.
Запускает все этапы анализа последовательно.
"""

import sys
import argparse
import os
import signal
from datetime import datetime

# Глобальная переменная для отслеживания прерывания
interrupted = False

def signal_handler(signum, frame):
    """Обработчик сигнала прерывания"""
    global interrupted
    interrupted = True
    print("\n\nПолучен сигнал прерывания (Ctrl+C)")
    print("Завершаю текущую операцию...")

def print_header(title: str) -> None:
    """Печатает заголовок раздела"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def run_parser(args) -> bool:
    """Запускает парсер для сбора данных"""
    print_header("1. СБОР ДАННЫХ С HABR")
    
    try:
        import parser
        parser.main()
        return True
    except KeyboardInterrupt:
        print("\nПарсинг прерван пользователем")
        return False
    except Exception as e:
        print(f"Ошибка при запуске парсера: {e}")
        return False

def run_database_builder(args) -> bool:
    """Запускает построение таблиц для DataLens"""
    print_header("2. ПОСТРОЕНИЕ ТАБЛИЦ ДЛЯ DATALENS")
    
    # Проверяем, есть ли сырые данные
    if not os.path.exists("results/raw_publications.csv"):
        print("Ошибка: Сначала нужно собрать данные (запустите с флагом --parse)")
        return False
    
    try:
        import database_builder
        database_builder.main()
        return True
    except Exception as e:
        print(f"Ошибка при построении таблиц: {e}")
        return False

def run_analyzer(args) -> bool:
    """Запускает аналитику"""
    print_header("3. АНАЛИЗ АКТИВНОСТИ ПОЛЬЗОВАТЕЛЕЙ")
    
    # Проверяем, есть ли таблицы для анализа
    if not os.path.exists("results/users.csv"):
        print("Ошибка: Сначала нужно построить таблицы (запустите с флагом --build)")
        return False
    
    try:
        import analyzer
        analyzer.main()
        return True
    except Exception as e:
        print(f"Ошибка при запуске анализатора: {e}")
        return False

def run_all(args) -> bool:
    """Запускает все этапы последовательно"""
    success = True
    
    # Парсинг данных
    if not run_parser(args):
        success = False
        print("Парсинг завершился с ошибками или был прерван")
        if not args.continue_on_error:
            return False
    
    # Построение таблиц
    if not run_database_builder(args):
        success = False
        print("Построение таблиц завершилось с ошибками")
        if not args.continue_on_error:
            return False
    
    # Анализ
    if not run_analyzer(args):
        success = False
        print("Анализ завершился с ошибками")
    
    return success

def show_status() -> None:
    """Показывает статус проекта"""
    print_header("СТАТУС ПРОЕКТА")
    
    files = [
        ("usernames.txt", "Список пользователей для анализа"),
        ("results/raw_publications.csv", "Сырые данные публикаций"),
        ("results/raw_user_counts.csv", "Сырые данные счетчиков"),
        ("results/publications.csv", "Таблица публикаций"),
        ("results/users.csv", "Таблица пользователей"),
        ("results/daily_activity.csv", "Таблица ежедневной активности"),
        ("results/themes.csv", "Таблица тем"),
        ("results/raw_publications_partial.csv", "Частичные данные (если есть)"),
        ("results/raw_user_counts_partial.csv", "Частичные счетчики (если есть)"),
    ]
    
    # Проверяем количество пользователей в файле
    user_count = 0
    if os.path.exists("usernames.txt"):
        with open("usernames.txt", 'r', encoding='utf-8') as f:
            user_count = sum(1 for line in f if line.strip())
    
    # Проверяем количество обработанных пользователей
    processed_count = 0
    if os.path.exists("results/raw_user_counts.csv"):
        with open("results/raw_user_counts.csv", 'r', encoding='utf-8') as f:
            processed_count = sum(1 for line in f) - 1  # минус заголовок
    
    print(f"Всего пользователей в usernames.txt: {user_count}")
    print(f"Уже обработано пользователей: {processed_count}")
    print()
    
    for filepath, description in files:
        exists = os.path.exists(filepath)
        size = ""
        if exists:
            size_bytes = os.path.getsize(filepath)
            if size_bytes > 1024*1024:
                size = f" ({size_bytes//(1024*1024)} МБ)"
            elif size_bytes > 1024:
                size = f" ({size_bytes//1024} КБ)"
            else:
                size = f" ({size_bytes} Б)"
        
        status = "✓" if exists else "✗"
        print(f"{status} {description:40} - {filepath}{size}")
    
    print("\nЗапустите анализ:")
    print("  python run_analysis.py --all        # Полный анализ")
    print("  python run_analysis.py --parse      # Только сбор данных")
    print("  python run_analysis.py --build      # Только построение таблиц")
    print("  python run_analysis.py --analyze    # Только анализ")

def create_project_structure() -> None:
    """Создает структуру проекта"""
    print_header("СОЗДАНИЕ СТРУКТУРЫ ПРОЕКТА")
    
    # Создаем необходимые директории
    os.makedirs("results", exist_ok=True)
    
    # Проверяем наличие списка пользователей
    if not os.path.exists("usernames.txt"):
        print("✗ Файл usernames.txt не найден!")
        print("  Создайте файл usernames.txt со списком пользователей Habr")
        print("  Например: https://habr.com/ru/users/username/")
    else:
        # Считаем количество пользователей
        with open("usernames.txt", 'r', encoding='utf-8') as f:
            user_count = sum(1 for line in f if line.strip())
        print(f"✓ Файл usernames.txt найден ({user_count} пользователей)")
    
    print("\nСтруктура проекта готова!")

def main():
    """Главная функция управляющего скрипта"""
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(
        description="Анализ активности пользователей Habr по публикациям",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python run_analysis.py --all          # Запустить полный анализ
  python run_analysis.py --parse        # Только сбор данных (можно прервать Ctrl+C)
  python run_analysis.py --build        # Только построение таблиц
  python run_analysis.py --analyze      # Только анализ
  python run_analysis.py --status       # Показать статус
  python run_analysis.py --init         # Инициализировать проект
  
Советы:
  - Парсинг может занять много времени (несколько часов)
  - Для прерывания парсинга нажмите Ctrl+C
  - Данные сохраняются автоматически каждые 20 пользователей
  - Можно продолжать с того места, где остановились
        """
    )
    
    parser.add_argument("--all", action="store_true", 
                       help="Запустить полный анализ (парсинг + построение + анализ)")
    parser.add_argument("--parse", action="store_true", 
                       help="Только сбор данных с Habr (прерывается Ctrl+C)")
    parser.add_argument("--build", action="store_true", 
                       help="Только построение таблиц для DataLens")
    parser.add_argument("--analyze", action="store_true", 
                       help="Только анализ и генерация отчета")
    parser.add_argument("--status", action="store_true", 
                       help="Показать статус проекта")
    parser.add_argument("--init", action="store_true", 
                       help="Инициализировать структуру проекта")
    parser.add_argument("--continue-on-error", action="store_true", 
                       help="Продолжать выполнение при ошибках")
    
    args = parser.parse_args()
    
    # Если нет аргументов, показываем справку
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    print("\n" + "="*80)
    print(" АНАЛИЗ АКТИВНОСТИ ПОЛЬЗОВАТЕЛЕЙ HABR")
    print("="*80)
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Выводим количество пользователей
    if os.path.exists("usernames.txt"):
        with open("usernames.txt", 'r', encoding='utf-8') as f:
            user_count = sum(1 for line in f if line.strip())
        print(f"Всего пользователей для анализа: {user_count}")
    else:
        print("Файл usernames.txt не найден!")
    
    # Выполняем выбранное действие
    if args.init:
        create_project_structure()
    elif args.status:
        show_status()
    elif args.parse:
        run_parser(args)
    elif args.build:
        run_database_builder(args)
    elif args.analyze:
        run_analyzer(args)
    elif args.all:
        run_all(args)
    
    print("\n" + "="*80)
    print(" ВЫПОЛНЕНИЕ ЗАВЕРШЕНО")
    print("="*80)

if __name__ == "__main__":
    main()