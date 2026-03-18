from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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
        "ئ": "ی",
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


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            )
        }
    )
    return session


def fetch_messages(
    channel_url: str,
    *,
    limit: int,
    retries: int,
    max_pages: int,
    min_delay: float,
) -> tuple[list[str], int]:
    base_channel_url = _strip_query(channel_url)
    url = channel_url
    seen_posts: set[str] = set()
    texts: list[str] = []
    session = make_session()
    pages = 0

    while pages < max_pages and len(texts) < limit:
        pages += 1
        html = _fetch_html_with_retry(session, url, retries=retries)
        if html is None:
            break

        soup = BeautifulSoup(html, "html.parser")
        blocks = soup.select("div.tgme_widget_message.js-widget_message")

        new_posts_this_page = 0
        min_post_id: int | None = None

        for block in blocks:
            post = block.get("data-post", "")
            if not post or post in seen_posts:
                continue
            seen_posts.add(post)
            new_posts_this_page += 1

            post_id = _extract_post_id(post)
            if post_id is not None:
                if min_post_id is None or post_id < min_post_id:
                    min_post_id = post_id

            text_node = block.select_one(".tgme_widget_message_text")
            text = text_node.get_text(" ", strip=True) if text_node else ""
            if text:
                texts.append(text)
            if len(texts) >= limit:
                break

        if len(texts) >= limit:
            break

        more = soup.select_one("a.tme_messages_more")
        if more and more.get("href"):
            href = more["href"]
            if href.startswith("/"):
                url = "https://t.me" + href
            elif href.startswith("http"):
                url = href
            else:
                break
        elif min_post_id is not None and new_posts_this_page > 0:
            # Fallback pagination used by Telegram channel preview pages.
            url = _with_before(base_channel_url, min_post_id)
        else:
            break

        if min_delay > 0:
            time.sleep(min_delay)

    return texts, pages


def _strip_query(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _with_before(base_url: str, before_id: int) -> str:
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["before"] = [str(before_id)]
    encoded = urlencode(query, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", encoded, ""))


def _extract_post_id(post_ref: str) -> int | None:
    # Example post_ref: "VahidOnline/74580"
    try:
        return int(post_ref.rsplit("/", 1)[-1])
    except (TypeError, ValueError):
        return None


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


def collect_counts(texts: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        for raw in PERSIAN_RE.findall(text):
            word = normalize_word(raw)
            if len(word) < 2:
                continue
            counter[word] += 1
    return counter


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Build ranked channel wordbank from multiple Telegram channels.")
    parser.add_argument(
        "--channels",
        nargs="+",
        default=[
            "https://t.me/s/telegram",
            "https://t.me/s/durov",
        ],
    )
    parser.add_argument("--limit-per-channel", type=int, default=1000)
    parser.add_argument("--min-freq", type=int, default=2)
    parser.add_argument("--top", type=int, default=12000)
    parser.add_argument("--retries", type=int, default=8)
    parser.add_argument("--max-pages", type=int, default=400)
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between page fetches (seconds)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("persian_encoder/data/priority_words.tsv"),
        help="TSV output: word<TAB>count",
    )
    args = parser.parse_args()

    merged: Counter[str] = Counter()
    total_messages = 0

    for channel in args.channels:
        texts, pages = fetch_messages(
            channel,
            limit=args.limit_per_channel,
            retries=max(1, args.retries),
            max_pages=max(1, args.max_pages),
            min_delay=max(0.0, args.delay),
        )
        total_messages += len(texts)
        per_channel = collect_counts(texts)
        merged.update(per_channel)
        print(f"channel={channel} messages={len(texts)} pages={pages} unique_words={len(per_channel)}")

    ranked = sorted(
        [(word, count) for word, count in merged.items() if count >= args.min_freq],
        key=lambda item: (-item[1], -len(item[0]), item[0]),
    )
    ranked = ranked[: args.top]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for word, count in ranked:
            handle.write(f"{word}\t{count}\n")

    print(f"total_messages={total_messages}")
    print(f"total_unique_words={len(merged)}")
    print(f"selected_words={len(ranked)}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
