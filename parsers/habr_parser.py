import csv
import os
from collections import Counter
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import requests
import xml.etree.ElementTree as ET


# ====== SETTINGS ======
f = open('usernames.txt')
AUTHORS = f.readlines()[:100]
f.close()


OUTPUT_DIR = "results_habr"
LIMIT = 100
LANGS = ["ru", "en"]
SECTIONS = ["articles", "posts", "news"]

MIN_THEME_POSTS = 50


# ====== IO ======
def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_csv(path: str, header: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ====== HELPERS ======
def normalize_login(s: str) -> str:
    s = s.strip().replace("https://", "").replace("http://", "")
    s = s.replace("habr.com/", "").replace("www.habr.com/", "")
    s = s.strip("/").lstrip("@")
    return s.split("/")[-1]


def add_or_replace_query_param(url: str, key: str, value: str) -> str:
    p = urlparse(url)
    qs = parse_qs(p.query)
    qs[key] = [value]
    return urlunparse(
        (p.scheme, p.netloc, p.path, p.params, urlencode(qs, doseq=True), p.fragment)
    )


def feed_url_candidates(login: str, section: str, lang: str) -> list[str]:
    base1 = f"https://habr.com/{lang}/rss/users/{login}/{section}/?fl={lang}"
    base2 = f"https://habr.com/{lang}/rss/users/{login}/publications/{section}/?fl={lang}"
    return [
        add_or_replace_query_param(base1, "limit", str(LIMIT)),
        add_or_replace_query_param(base2, "limit", str(LIMIT)),
    ]


def _tag(elem, name: str) -> bool:
    return elem.tag.lower().endswith(name.lower())


# ====== DATA ======
@dataclass
class FeedPost:
    hubs: list[str]


# ====== FEED PARSER ======
def parse_feed(xml_text: str) -> list[FeedPost]:
    root = ET.fromstring(xml_text)
    posts: list[FeedPost] = []

    # Atom
    if _tag(root, "feed"):
        for entry in root.iter():
            if not _tag(entry, "entry"):
                continue

            hubs = []
            for child in entry:
                if _tag(child, "category"):
                    term = child.attrib.get("term")
                    if term:
                        hubs.append(term)

            posts.append(FeedPost(hubs=hubs))
        return posts

    # RSS
    for item in root.iter():
        if not _tag(item, "item"):
            continue

        hubs = []
        for child in item:
            if _tag(child, "category") and child.text:
                hubs.append(child.text.strip())

        posts.append(FeedPost(hubs=hubs))

    return posts


# ====== FETCH ======
HEADERS = {
    "User-Agent": "habr-theme-parser/1.2",
    "Accept": "application/rss+xml, application/atom+xml, text/xml",
}


def fetch_posts(login: str, section: str, session: requests.Session) -> list[FeedPost]:
    all_posts: list[FeedPost] = []

    for lang in LANGS:
        for url in feed_url_candidates(login, section, lang):
            try:
                r = session.get(url, headers=HEADERS, timeout=30)
                if r.status_code != 200:
                    continue
                all_posts.extend(parse_feed(r.text))
            except Exception:
                continue

    return all_posts


# ====== MAIN ======
def main():
    ensure_dir(OUTPUT_DIR)
    session = requests.Session()

    csv_rows = []
    global_theme_counter = Counter()

    total_authors = len(AUTHORS)

    for idx, raw_login in enumerate(AUTHORS, start=1):
        login = normalize_login(raw_login)
        print(f"\n[{idx}/{total_authors}] Processing {login}")

        try:
            all_posts: list[FeedPost] = []

            for section in SECTIONS:
                all_posts.extend(fetch_posts(login, section, session))

            hub_freq = Counter()
            for post in all_posts:
                for hub in post.hubs:
                    hub_freq[hub] += 1

            valid_themes = {
                hub for hub, cnt in hub_freq.items()
                if cnt >= MIN_THEME_POSTS
            }

            theme_counter = Counter()

            for post in all_posts:
                matched = False
                for hub in post.hubs:
                    if hub in valid_themes:
                        theme_counter[hub] += 1
                        global_theme_counter[hub] += 1
                        matched = True

                if not matched:
                    theme_counter["other"] += 1
                    global_theme_counter["other"] += 1

            # вывод по автору
            for theme, count in theme_counter.most_common():
                print(f"  {theme}: {count}")
                csv_rows.append([login, theme, count])

        except Exception as e:
            print(f"  ERROR for {login}: {e}")
            continue

    write_csv(
        os.path.join(OUTPUT_DIR, "author_theme_stats.csv"),
        ["login", "theme", "posts_count"],
        csv_rows,
    )

    # ====== ФИНАЛЬНАЯ СВОДКА ======
    print("\n=== FINAL THEMES SUMMARY ===")
    for theme, count in global_theme_counter.most_common():
        print(f"{theme}: {count}")

    print("\nDone.")


if __name__ == "__main__":
    main()
