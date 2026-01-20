from bs4 import BeautifulSoup

# Загружаем HTML из файла
with open("Два по сто_ самые читаемые статьи и авторы Хабра и ГТ _ Хабр.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Попробуем найти все ссылки на авторов
authors = []
for a in soup.find_all("a"):
    href = a.get("href", "")
    if "/users/" in href:  # ссылка на профиль автора
        name = a.get_text(strip=True)
        if name and name not in authors:
            authors.append(name)

authors = authors[:-1]
print(len(authors))


f = open('res_attempt_2.txt', 'w')
for i in authors:
    f.write(i + '\n')
print(authors)

f.close()
