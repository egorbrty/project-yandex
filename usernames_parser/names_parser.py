import requests
from bs4 import BeautifulSoup
from collections import Counter
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


# ===== TLS Adapter для обхода SSL ошибок на Windows =====
class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers("DEFAULT@SECLEVEL=1")  # понижает требования к шифрам
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers("DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = context
        return super().proxy_manager_for(*args, **kwargs)

# ===== Настройка сессии =====
session = requests.Session()
session.mount("https://", TLSAdapter())
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ===== Парсер авторов =====
authors_counter = Counter()
pages_to_parse = 50

for page in range(1, pages_to_parse + 1):
    url = f"https://habr.com/ru/all/page{page}/"
    try:
        resp = session.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[!] Ошибка запроса страницы {page}: {e}")
        continue

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article")

    for a in articles:
        author_tag = a.select_one("a.tm-user-info__username")
        if author_tag:
            authors_counter[author_tag.text.strip()] += 1

    print(f"[+] Страница {page} обработана, всего уникальных авторов: {len(authors_counter)}")
    time.sleep(1 + random.random())  # антибан

# ===== Топ-500 авторов =====


f = open('res.txt', 'w')

top_authors = authors_counter.most_common(1000)
print("\n=== ТОП-500 авторов Хабра ===")
for i, (author, count) in enumerate(top_authors, 1):
    f.write(author + '\n')
f.close()
