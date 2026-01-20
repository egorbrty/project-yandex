import csv
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

# ====== SETTINGS ======
f = open('usernames.txt')
AUTHORS = f.readlines()
f.close()

OUTPUT_DIR = "results_habr"
LIMIT = 100
LANGS = ["ru", "en"]
SECTIONS = ["articles", "posts", "news"]

MIN_THEME_POSTS = 3

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
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(qs, doseq=True), p.fragment))

def feed_url_candidates(login: str, section: str, lang: str) -> list[str]:
    base1 = f"https://habr.com/{lang}/rss/users/{login}/{section}/?fl={lang}"
    base2 = f"https://habr.com/{lang}/rss/users/{login}/publications/{section}/?fl={lang}"
    return [
        add_or_replace_query_param(base1, "limit", str(LIMIT)),
        add_or_replace_query_param(base2, "limit", str(LIMIT)),
    ]

def _tag(elem, name: str) -> bool:
    return elem.tag.lower().endswith(name.lower())

def parse_datetime(text: str):
    """Парсим дату из RSS или Atom в UTC"""
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

# ====== DATA ======
@dataclass(frozen=True)
class FeedPost:
    uid: str
    hubs: tuple[str]
    date_utc: datetime

# ====== FEED PARSER ======
def parse_feed(xml_text: str) -> list[FeedPost]:
    root = ET.fromstring(xml_text)
    posts = []

    # Atom
    if _tag(root, "feed"):
        for entry in root.iter():
            if not _tag(entry, "entry"):
                continue
            uid = None
            hubs = []
            date_utc = None
            for child in entry:
                if _tag(child, "id") or _tag(child, "link"):
                    uid = (child.text or "").strip()
                elif _tag(child, "category"):
                    term = (child.attrib.get("term") or "").strip().lower()
                    if term:
                        hubs.append(term)
                elif _tag(child, "published") or _tag(child, "updated"):
                    dt = parse_datetime(child.text)
                    if dt:
                        date_utc = dt
            if uid and date_utc:
                posts.append(FeedPost(uid=uid, hubs=tuple(set(hubs)), date_utc=date_utc))
        return posts

    # RSS
    for item in root.iter():
        if not _tag(item, "item"):
            continue
        uid = None
        hubs = []
        date_utc = None
        for child in item:
            if _tag(child, "guid") or _tag(child, "link"):
                uid = (child.text or "").strip()
            elif _tag(child, "category") and child.text:
                hubs.append(child.text.strip().lower())
            elif _tag(child, "pubDate") and child.text:
                dt = parse_datetime(child.text)
                if dt:
                    date_utc = dt
        if uid and date_utc:
            posts.append(FeedPost(uid=uid, hubs=tuple(set(hubs)), date_utc=date_utc))
    return posts

# ====== FETCH ======
HEADERS = {
    "User-Agent": "habr-theme-parser-4.0",
    "Accept": "application/rss+xml, application/atom+xml, text/xml",
}

def fetch_posts(login: str, section: str, session: requests.Session) -> list[FeedPost]:
    all_posts = []
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
    total_authors = len(AUTHORS)
    post_number = 1  # счётчик публикаций

    for idx, raw_login in enumerate(AUTHORS, start=1):
        login = normalize_login(raw_login)
        print(f"\n[{idx}/{total_authors}] Processing {login}")

        try:
            all_posts = []
            for section in SECTIONS:
                all_posts.extend(fetch_posts(login, section, session))

            # Дедупликация по uid
            unique_posts = list({p.uid: p for p in all_posts}.values())

            # Частота хабов для определения популярных тем
            hub_freq = Counter()
            for post in unique_posts:
                for hub in post.hubs:
                    hub_freq[hub] += 1
            valid_themes = {hub for hub, cnt in hub_freq.items() if cnt >= MIN_THEME_POSTS}

            for post in unique_posts:
                # Если пост не имеет хабов → other
                hubs_to_write = [hub for hub in post.hubs if hub in valid_themes]
                if not hubs_to_write:
                    hubs_to_write = ["other"]

                # Формируем строку CSV
                csv_rows.append([
                    post_number,
                    login,
                    ",".join(hubs_to_write),
                    post.date_utc.strftime("%Y-%m-%d")
                ])
                post_number += 1

        except Exception as e:
            print(f"  ERROR for {login}: {e}")
            continue

    write_csv(
        os.path.join(OUTPUT_DIR, "author_post_table.csv"),
        ["post_number", "author", "themes", "date_utc"],
        csv_rows,
    )

    print("\nDone.")

if __name__ == "__main__":
    main()
