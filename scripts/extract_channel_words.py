from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from pathlib import Path

import requests
from bs4 import BeautifulSoup


PERSIAN_RE = re.compile(r"[آ-ی]+(?:\u200c[آ-ی]+)*")
BASE_NORMALIZATION = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
        "ـ": "",
    }
)
DIACRITICS_RE = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
MULTI_ZWNJ_RE = re.compile(r"\u200c+")


def normalize_word(word: str) -> str:
    normalized = word.strip().translate(BASE_NORMALIZATION)
    normalized = DIACRITICS_RE.sub("", normalized)
    normalized = MULTI_ZWNJ_RE.sub("\u200c", normalized)
    return normalized


def fetch_messages(channel_url: str, limit: int, *, retries: int = 5, max_pages: int | None = None) -> list[str]:
    url = channel_url
    seen_posts: set[str] = set()
    texts: list[str] = []
    pages_budget = max_pages if max_pages is not None else max(60, (limit // 10) + 20)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            )
        }
    )

    for _ in range(pages_budget):
        html = _fetch_html_with_retry(session, url, retries=retries)
        if html is None:
            break
        soup = BeautifulSoup(html, "html.parser")
        blocks = soup.select("div.tgme_widget_message.js-widget_message")

        for block in blocks:
            post = block.get("data-post", "")
            if not post or post in seen_posts:
                continue
            seen_posts.add(post)

            text_node = block.select_one(".tgme_widget_message_text")
            text = text_node.get_text(" ", strip=True) if text_node else ""
            if text:
                texts.append(text)
            if len(texts) >= limit:
                return texts

        more = soup.select_one("a.tme_messages_more")
        if more and more.get("href"):
            href = more["href"]
            if href.startswith("/"):
                url = "https://t.me" + href
            elif href.startswith("http"):
                url = href
            else:
                break
            continue

        break

    return texts


def _fetch_html_with_retry(session: requests.Session, url: str, *, retries: int) -> str | None:
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            if attempt >= retries:
                return None
            time.sleep(delay)
            delay = min(delay * 2.0, 8.0)
    return None


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Extract top Persian words from Telegram channel posts")
    parser.add_argument("--channel", default="https://t.me/s/durov")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--min-freq", type=int, default=2)
    parser.add_argument("--top", type=int, default=200)
    parser.add_argument("--retries", type=int, default=5, help="Per-page HTTP retries")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages to crawl")
    parser.add_argument("--output", type=Path, default=None, help="Optional output text file")
    args = parser.parse_args()

    texts = fetch_messages(args.channel, args.limit, retries=max(1, args.retries), max_pages=args.max_pages)
    counter: Counter[str] = Counter()

    for text in texts:
        for raw in PERSIAN_RE.findall(text):
            word = normalize_word(raw)
            if len(word) < 2:
                continue
            counter[word] += 1

    words = [w for w, c in counter.most_common(args.top) if c >= args.min_freq]
    content = "\n".join(words)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + ("\n" if content else ""), encoding="utf-8")
        print(f"written={args.output} words={len(words)} messages={len(texts)}")
        return

    print(content)


if __name__ == "__main__":
    main()
