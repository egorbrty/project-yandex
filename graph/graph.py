import pandas as pd
import itertools
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

def count_theme_pairs(excel_file, output_file, min_cooccurrence=2):
    """
    Анализирует Excel-файл с постами и темами, считает частоту совместного использования тем
    
    Параметры:
    excel_file: путь к исходному Excel-файлу
    output_file: путь для сохранения результата
    min_cooccurrence: минимальное количество совместных упоминаний для включения в результат
    """
    
    # 1. Загружаем данные
    print(f"Загружаем данные из {excel_file}...")
    df = pd.read_excel(excel_file)
    
    # 2. Очищаем и обрабатываем темы
    print("Обрабатываю темы...")
    posts_with_themes = []
    
    for idx, row in df.iterrows():
        themes_str = row['themes']
        
        # Пропускаем пустые темы и 'other'
        if pd.isna(themes_str) or not str(themes_str).strip():
            continue
            
        themes_str = str(themes_str)
        if themes_str.lower() == 'other':
            continue
        
        # Разделяем темы по запятым и очищаем
        themes = [t.strip() for t in themes_str.split(',')]
        # Удаляем пустые строки
        themes = [t for t in themes if t]
        
        if themes:  # Если есть хотя бы одна тема
            posts_with_themes.append(themes)
    
    print(f"Обработано {len(posts_with_themes)} постов с темами")
    
    # 3. Считаем пары тем
    print("Считаю пары тем...")
    all_pairs_counter = Counter()
    
    for themes in posts_with_themes:
        # Сортируем темы для уникальности пар
        sorted_themes = sorted(themes)
        
        # Генерируем все уникальные пары для этого поста
        for pair in itertools.combinations(sorted_themes, 2):
            all_pairs_counter[pair] += 1
    
    # 4. Фильтруем и преобразуем результат
    print("Форматирую результат...")
    pairs_data = []
    
    for (theme1, theme2), count in all_pairs_counter.items():
        if count >= min_cooccurrence:
            pairs_data.append({
                'Source': theme1,
                'Target': theme2,
                'Weight': count,
                'Pair': f"{theme1} - {theme2}"
            })
    
    # Сортируем по весу (частоте)
    pairs_df = pd.DataFrame(pairs_data)
    pairs_df = pairs_df.sort_values('Weight', ascending=False)
    
    # 5. Сохраняем результат
    print(f"Сохраняю результат в {output_file}...")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Основная таблица с парами
        pairs_df[['Source', 'Target', 'Weight']].to_excel(
            writer, sheet_name='Theme Pairs', index=False
        )
        
        # Дополнительная статистика
        stats_data = {
            'Метрика': [
                'Всего постов с темами',
                'Всего уникальных тем',
                'Всего пар тем (совместные упоминания)',
                'Пар после фильтрации (минимум 2 совместных)',
                'Самая частая пара',
                'Максимальный вес',
                'Средний вес'
            ],
            'Значение': [
                len(posts_with_themes),
                len(set([t for themes in posts_with_themes for t in themes])),
                len(all_pairs_counter),
                len(pairs_df),
                f"{pairs_df.iloc[0]['Source']} - {pairs_df.iloc[0]['Target']}" if len(pairs_df) > 0 else "Нет данных",
                pairs_df['Weight'].max() if len(pairs_df) > 0 else 0,
                round(pairs_df['Weight'].mean(), 2) if len(pairs_df) > 0 else 0
            ]
        }
        pd.DataFrame(stats_data).to_excel(
            writer, sheet_name='Statistics', index=False
        )
        
        # Топ-20 самых частых пар
        pairs_df.head(20).to_excel(
            writer, sheet_name='Top 20 Pairs', index=False
        )
    
    print(f"Готово! Результат сохранен в {output_file}")
    print(f"\nТоп-10 самых частых пар тем:")
    for i, row in pairs_df.head(10).iterrows():
        print(f"  {row['Source']} ↔ {row['Target']}: {row['Weight']} раз")
    
    return pairs_df

def main():
    # Конфигурация
    INPUT_FILE = 'author_post_table_themes_fixed.xlsx'  # Ваш исходный файл
    OUTPUT_FILE = 'theme_pairs_analysis.xlsx'          # Файл для результата
    MIN_COOCCURRENCE = 2  # Минимальное количество совместных упоминаний
    
    try:
        # Запускаем анализ
        result_df = count_theme_pairs(
            excel_file=INPUT_FILE,
            output_file=OUTPUT_FILE,
            min_cooccurrence=MIN_COOCCURRENCE
        )
        
        print(f"\n📊 Статистика:")
        print(f"- Найдено пар тем: {len(result_df)}")
        print(f"- Максимальная связь: {result_df.iloc[0]['Weight'] if len(result_df) > 0 else 0}")
        print(f"- Средняя сила связи: {round(result_df['Weight'].mean(), 2) if len(result_df) > 0 else 0}")
        
        # Дополнительно: фильтрация по интересующим темам
        interesting_themes = ['open source', 'python', 'искусственный интеллект', 
                             'программирование', 'разработка игр', 'информационная безопасность']
        
        print(f"\n🔍 Связи для интересующих тем:")
        for theme in interesting_themes:
            theme_connections = result_df[
                (result_df['Source'] == theme) | (result_df['Target'] == theme)
            ]
            if not theme_connections.empty:
                print(f"\n{theme}:")
                for _, row in theme_connections.head(5).iterrows():
                    other_theme = row['Target'] if row['Source'] == theme else row['Source']
                    print(f"  ↔ {other_theme}: {row['Weight']}")
        
    except FileNotFoundError:
        print(f"Ошибка: Файл {INPUT_FILE} не найден!")
        print("Убедитесь, что файл находится в той же папке, что и программа.")
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    main()
