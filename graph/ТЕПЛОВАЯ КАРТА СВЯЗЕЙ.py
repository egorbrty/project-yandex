import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import numpy as np
from matplotlib import cm

def create_elite_network(excel_file, top_n_themes=15, min_connections=5, min_weight=5):
    """
    Создает элитную сеть только для самых-самых значимых тем
    """
    
    # 1. Загружаем данные
    print("📊 Загружаю данные...")
    df = pd.read_excel(excel_file, sheet_name='Theme Pairs')
    
    # 2. Определяем самые элитные темы
    print("🔍 Определяю элитные темы...")
    
    theme_power = Counter()
    for _, row in df.iterrows():
        theme_power[row['Source']] += row['Weight']
        theme_power[row['Target']] += row['Weight']
    
    elite_themes = [theme for theme, _ in theme_power.most_common(top_n_themes)]
    
    print(f"✅ Отобрано {len(elite_themes)} ЭЛИТНЫХ тем:")
    for i, (theme, power) in enumerate(theme_power.most_common(top_n_themes), 1):
        print(f"  {i:2d}. {theme:35s} (общая сила: {power})")
    
    # 3. Фильтруем только ОЧЕНЬ сильные связи
    print("\n🔗 Фильтрую ТОЛЬКО сильные связи...")
    
    mask = (
        (df['Source'].isin(elite_themes)) & 
        (df['Target'].isin(elite_themes)) &
        (df['Weight'] >= min_weight)
    )
    
    elite_pairs = df[mask].copy()
    
    if not elite_pairs.empty:
        original_max_weight = elite_pairs['Weight'].max()
        print(f"📊 Максимальный вес в отфильтрованных данных: {original_max_weight}")
    
    elite_pairs = elite_pairs.nlargest(30, 'Weight')
    
    print(f"✅ Оставлено {len(elite_pairs)} СИЛЬНЕЙШИХ связей")
    
    # 4. Создаем элитный граф
    G = nx.Graph()
    
    for _, row in elite_pairs.iterrows():
        G.add_edge(row['Source'], row['Target'], weight=row['Weight'])
    
    isolated_nodes = [node for node in G.nodes() if G.degree(node) == 0]
    G.remove_nodes_from(isolated_nodes)
    
    print(f"📈 В графе: {G.number_of_nodes()} ключевых тем, {G.number_of_edges()} ключевых связей")
    
    return G, elite_pairs, elite_themes

def visualize_elite_network(G, figsize=(18, 14)):
    """
    Визуализирует элитную сеть связей
    """
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Используем spring layout
    pos = nx.spring_layout(G, k=2.5, iterations=150, seed=42)
    
    # 1. Вычисляем характеристики узлов
    node_degrees = dict(G.degree())
    if not node_degrees:
        print("⚠️  Нет узлов для визуализации")
        return plt
    
    max_degree = max(node_degrees.values())
    min_degree = min(node_degrees.values())
    
    # Размер узлов
    node_sizes = []
    for node in G.nodes():
        degree = node_degrees[node]
        normalized = (np.log1p(degree) - np.log1p(min_degree)) / (np.log1p(max_degree) - np.log1p(min_degree))
        size = 600 + 1800 * normalized
        node_sizes.append(size)
    
    # 2. Рисуем связи
    edges = list(G.edges())
    if not edges:
        print("⚠️  Нет связей для визуализации")
        return plt
    
    edge_weights = [G[u][v]['weight'] for u, v in edges]
    max_weight = max(edge_weights)
    min_weight = min(edge_weights)
    
    print(f"📊 Веса связей: min={min_weight}, max={max_weight}")
    
    # Рисуем связи с градиентом
    for (u, v), weight in zip(edges, edge_weights):
        if max_weight == min_weight:
            normalized_weight = 0.5
        else:
            normalized_weight = (weight - min_weight) / (max_weight - min_weight)
        
        # Более сбалансированная толщина
        thickness = 0.8 + 3.2 * (np.log1p(weight) / np.log1p(max_weight))
        
        # Цвета связей
        if normalized_weight > 0.8:
            color = '#1B4F72'
            alpha = 0.9
        elif normalized_weight > 0.6:
            color = '#2874A6'
            alpha = 0.8
        elif normalized_weight > 0.4:
            color = '#3498DB'
            alpha = 0.7
        elif normalized_weight > 0.2:
            color = '#85C1E9'
            alpha = 0.6
        else:
            color = '#D6EAF8'
            alpha = 0.5
        
        nx.draw_networkx_edges(
            G, pos, edgelist=[(u, v)],
            width=thickness,
            alpha=alpha,
            edge_color=color,
            style='solid',
            ax=ax
        )
    
    # 3. Рисуем узлы
    centrality = nx.degree_centrality(G)
    if centrality:
        centrality_values = list(centrality.values())
        max_centr = max(centrality_values) if centrality_values else 1
        if max_centr > 0:
            normalized_centrality = {node: centr/max_centr for node, centr in centrality.items()}
        else:
            normalized_centrality = centrality
    else:
        normalized_centrality = {node: 0 for node in G.nodes()}
    
    node_colors = [normalized_centrality[node] for node in G.nodes()]
    
    nodes = nx.draw_networkx_nodes(
        G, pos,
        node_size=node_sizes,
        node_color=node_colors,
        cmap=plt.cm.plasma,
        alpha=0.95,
        edgecolors='white',
        linewidths=2.5,
        vmin=0,
        vmax=1,
        ax=ax
    )
    
    # 4. Подписи узлов
    for node, (x, y) in pos.items():
        node_idx = list(G.nodes()).index(node)
        font_size = 9 + (node_sizes[node_idx] / 2400) * 5
        
        ax.text(x, y, node, 
                fontsize=font_size,
                fontweight='bold',
                ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.3", 
                         facecolor="white", 
                         alpha=0.85, 
                         edgecolor="gray",
                         linewidth=1))
    
    # 5. Цветовая шкала - сдвигаем ПРАВЕЕ с помощью shrink и pad
    if node_colors:
        cbar = plt.colorbar(nodes, ax=ax, shrink=0.65, pad=0.03)
        cbar.set_label('Центральность (Degree Centrality)', fontsize=11, fontweight='bold', labelpad=10)
        cbar.ax.tick_params(labelsize=9)
    
    # 6. Заголовок
    title_text = 'ЯДРО СЕТИ: самые сильные связи между ключевыми темами\n' \
                 '▸ Размер узла = количество связей\n' \
                 '▸ Толщина линии = сила связи\n' \
                 '▸ Цвет узла = центральность в сети'
    
    ax.set_title(title_text, fontsize=14, pad=20, fontweight='bold')
    
    ax.axis('off')
    
    # 7. Статистика - РИСУЕМ ПРЯМО НА ГРАФИКЕ, а не отдельной осью
    if edges:
        strongest_edge_idx = np.argmax(edge_weights)
        (u, v) = edges[strongest_edge_idx]
        weight = edge_weights[strongest_edge_idx]
        
        if centrality:
            most_central = max(centrality.items(), key=lambda x: x[1])
            central_theme, central_value = most_central
        
        stats_text = f"◉ Тем: {G.number_of_nodes()}\n" \
                     f"◉ Связей: {G.number_of_edges()}\n" \
                     f"◉ Сила связей: {min_weight}-{max_weight}\n"
        
        if 'central_theme' in locals():
            stats_text += f"◉ Самая центральная:\n" \
                         f"  {central_theme}"
        
        # Рисуем текст прямо на графике
        ax.text(0.02, 0.98, stats_text,
                transform=ax.transAxes,
                fontsize=10,
                fontweight='medium',
                verticalalignment='top',
                bbox=dict(boxstyle="round,pad=0.5",
                         facecolor="white",
                         alpha=0.9,
                         edgecolor="gray",
                         linewidth=1))
    
    # 8. Легенда - тоже рисуем прямо на графике
    legend_text = "ПОЯСНЕНИЯ:\n" \
                  "▸ Толщина линий = сила связи\n" \
                  "▸ Цвет узлов = центральность\n" \
                  "▸ Желтые = высокая\n" \
                  "▸ Фиолетовые = низкая"
    
    ax.text(0.02, 0.02, legend_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment='bottom',
            bbox=dict(boxstyle="round,pad=0.4",
                     facecolor="white",
                     alpha=0.8,
                     edgecolor="lightgray"))
    
    # 9. Важно: tight_layout с большими отступами
    plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.95])  # [left, bottom, right, top]
    
    return plt

def plot_elite_connections(df, top_n=12):
    """
    График только самых-самых сильных связей
    """
    
    elite_connections = df.nlargest(top_n, 'Weight')
    
    if elite_connections.empty:
        print("⚠️  Нет данных для графика связей")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "Нет данных для отображения", 
                ha='center', va='center', fontsize=14)
        ax.set_title(f'ТОП-{top_n} САМЫХ СИЛЬНЫХ СВЯЗЕЙ', 
                    fontsize=14, pad=20, fontweight='bold')
        ax.axis('off')
        plt.tight_layout()
        return plt
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    n_bars = len(elite_connections)
    colors = cm.plasma(np.linspace(0.2, 0.9, n_bars))
    
    bars = ax.barh(range(n_bars), elite_connections['Weight'], 
                   color=colors, edgecolor='black', linewidth=1.2, 
                   height=0.7)
    
    ax.set_yticks(range(n_bars))
    
    y_labels = []
    for _, row in elite_connections.iterrows():
        source = row['Source']
        target = row['Target']
        if len(source) > 30:
            source = source[:28] + "..."
        if len(target) > 30:
            target = target[:28] + "..."
        y_labels.append(f"{source} — {target}")
    
    ax.set_yticklabels(y_labels, fontsize=11, fontweight='medium')
    
    ax.set_xlabel('Количество совместных упоминаний', fontsize=12, fontweight='bold')
    
    title = f'ТОП-{min(top_n, n_bars)} САМЫХ СИЛЬНЫХ СВЯЗЕЙ'
    ax.set_title(title, fontsize=16, pad=25, fontweight='bold')
    
    for i, (bar, weight) in enumerate(zip(bars, elite_connections['Weight'])):
        ax.text(weight + (max(elite_connections['Weight']) * 0.01), 
                bar.get_y() + bar.get_height()/2, 
                f"{int(weight)}", 
                va='center', 
                fontsize=11, 
                fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, edgecolor='gray'))
    
    ax.grid(axis='x', alpha=0.3, linestyle='--', linewidth=1.0)
    ax.set_axisbelow(True)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['left'].set_linewidth(1.5)
    
    plt.subplots_adjust(left=0.35, right=0.95)
    plt.tight_layout()
    
    return plt

def main():
    EXCEL_FILE = 'theme_pairs_analysis.xlsx'
    OUTPUT_PREFIX = 'elite_network'
    
    print("=" * 60)
    print("🏆 СОЗДАНИЕ ЭЛИТНОЙ СЕТИ СВЯЗЕЙ")
    print("(все значимые темы и сильные связи)")
    print("=" * 60)
    
    G, elite_df, elite_themes = create_elite_network(
        excel_file=EXCEL_FILE,
        top_n_themes=12,
        min_connections=3,
        min_weight=5
    )
    
    if G.number_of_nodes() == 0:
        print("\n⚠️  Слишком высокие пороги! Попробуйте:")
        print("   - Уменьшить min_weight до 4")
        print("   - Уменьшить min_connections до 2")
        print("   - Увеличить top_n_themes до 15")
        return
    
    # 1. Визуализируем элитную сеть
    print("\n🎨 Визуализирую элитную сеть...")
    plt1 = visualize_elite_network(G, figsize=(16, 12))  # Чуть уменьшил размер
    plt1.savefig(f'{OUTPUT_PREFIX}_graph.png', dpi=300, bbox_inches='tight')
    plt1.show()
    
    # 2. График самых сильных связей
    print("\n📊 Строю график самых сильных связей...")
    plt2 = plot_elite_connections(elite_df, top_n=15)
    plt2.savefig(f'{OUTPUT_PREFIX}_top_connections.png', dpi=300, bbox_inches='tight')
    plt2.show()
    
    # 3. Сохраняем элитные данные
    elite_df.to_excel(f'{OUTPUT_PREFIX}_data.xlsx', index=False)
    
    print("\n" + "=" * 60)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("=" * 60)
    print(f"📁 Сохраненные файлы:")
    print(f"   📍 {OUTPUT_PREFIX}_graph.png")
    print(f"   📍 {OUTPUT_PREFIX}_top_connections.png")
    print(f"   📍 {OUTPUT_PREFIX}_data.xlsx")
    
    if not elite_df.empty:
        print(f"\n📊 СТАТИСТИКА СЕТИ:")
        print(f"   • Ключевых тем: {G.number_of_nodes()}")
        print(f"   • Ключевых связей: {G.number_of_edges()}")
        
        centrality = nx.degree_centrality(G)
        print(f"\n🏆 ТОП-5 ЦЕНТРАЛЬНЫХ ТЕМ:")
        for theme, centr in sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]:
            connections = G.degree(theme)
            print(f"   {theme:25s} | Центральность: {centr:.3f} | Связей: {connections}")
        
        print(f"\n💪 САМЫЕ СИЛЬНЫЕ СВЯЗИ:")
        top_5_pairs = elite_df.nlargest(5, 'Weight')
        for _, row in top_5_pairs.iterrows():
            print(f"   {row['Source']:20s} ↔ {row['Target']:20s} | {row['Weight']} раз")
        
        if G.number_of_nodes() > 1:
            density = nx.density(G)
            avg_degree = sum(dict(G.degree()).values()) / G.number_of_nodes()
            print(f"\n📐 ПЛОТНОСТЬ СЕТИ: {density:.3f}")
            print(f"📐 СРЕДНЕЕ КОЛИЧЕСТВО СВЯЗЕЙ НА ТЕМУ: {avg_degree:.1f}")
            
            if G.number_of_nodes() > 2:
                clustering = nx.average_clustering(G)
                print(f"📐 СРЕДНИЙ КОЭФФИЦИЕНТ КЛАСТЕРИЗАЦИИ: {clustering:.3f}")

if __name__ == "__main__":
    main()
