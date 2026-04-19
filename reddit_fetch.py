import requests
import time
import random
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }


def fetch_reddit_posts(keyword: str, limit: int = 100) -> list[dict]:
    """
    Fetch Reddit posts via RSS feed — no API key, no bot blocking.
    RSS is always open on Reddit regardless of server IP.
    """
    posts = []

    # Multiple RSS feeds to maximize results
    feeds = [
        f"https://www.reddit.com/search.rss?q={quote(keyword)}&sort=relevance&t=year&limit=50",
        f"https://www.reddit.com/search.rss?q={quote(keyword)}+problem&sort=new&limit=50",
        f"https://www.reddit.com/search.rss?q={quote(keyword)}+frustrated&sort=relevance&limit=50",
    ]

    permalinks_seen = set()

    for feed_url in feeds:
        try:
            resp = requests.get(feed_url, headers=_get_headers(), timeout=15)
            print(f"[rss] {feed_url[:80]} → status {resp.status_code}")

            if resp.status_code != 200:
                time.sleep(1)
                continue

            # Parse RSS XML
            items = _parse_rss(resp.text)
            print(f"[rss] Parsed {len(items)} items")

            for item in items:
                permalink = item.get("permalink", "")
                if not permalink or permalink in permalinks_seen:
                    continue
                permalinks_seen.add(permalink)

                # Add the post text
                text = item.get("text", "").strip()
                if text and len(text) > 20:
                    posts.append({
                        "text": text,
                        "source": "post",
                        "subreddit": item.get("subreddit", ""),
                        "url": item.get("url", "")
                    })

                # Fetch comments for this thread
                comments = _fetch_comments(permalink)
                posts.extend(comments)
                time.sleep(0.5)

                if len(posts) >= limit:
                    break

            time.sleep(1)

        except Exception as e:
            print(f"[rss] Feed failed: {e}")
            continue

        if len(posts) >= limit:
            break

    print(f"[rss] Total posts collected: {len(posts)}")
    return posts[:limit]


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse Reddit RSS XML and extract post data."""
    items = []

    try:
        root = ET.fromstring(xml_text)

        # Reddit RSS namespace
        ns = {
            "media": "http://search.yahoo.com/mrss/",
        }

        # Find all <entry> tags (Atom format) or <item> tags (RSS format)
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        if not entries:
            # Try standard RSS <item>
            entries = root.findall(".//item")

        for entry in entries:
            try:
                # Atom format
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                content_el = entry.find("{http://www.w3.org/2005/Atom}content")
                category_el = entry.find("{http://www.w3.org/2005/Atom}category")

                title = title_el.text if title_el is not None else ""
                url = link_el.get("href", "") if link_el is not None else ""
                content_raw = content_el.text if content_el is not None else ""
                subreddit = category_el.get("term", "") if category_el is not None else ""

                # Extract permalink from URL
                permalink_match = re.search(r'reddit\.com(/r/[^"&\s?#]+)', url)
                permalink = permalink_match.group(1) if permalink_match else ""

                # Strip HTML tags from content
                content_clean = re.sub(r"<[^>]+>", " ", content_raw or "")
                content_clean = re.sub(r"\s+", " ", content_clean).strip()

                # Combine title + content
                text = f"{title}. {content_clean}".strip() if content_clean else title

                if title or text:
                    items.append({
                        "text": text[:600],
                        "permalink": permalink,
                        "url": url,
                        "subreddit": subreddit
                    })

            except Exception:
                continue

    except ET.ParseError as e:
        print(f"[rss] XML parse error: {e}")

    return items


def _fetch_comments(permalink: str) -> list[dict]:
    """Fetch top comments from a Reddit thread JSON."""
    results = []
    if not permalink:
        return results

    url = f"https://www.reddit.com{permalink}.json?limit=8&sort=top"

    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json",
            },
            timeout=12
        )

        if resp.status_code != 200:
            return results

        data = resp.json()
        if len(data) < 2:
            return results

        subreddit = ""
        try:
            subreddit = data[0]["data"]["children"][0]["data"].get("subreddit", "")
        except Exception:
            pass

        comments = data[1]["data"]["children"]
        for c in comments[:6]:
            body = c.get("data", {}).get("body", "").strip()
            if body and body not in ("[deleted]", "[removed]") and len(body) > 20:
                results.append({
                    "text": body,
                    "source": "comment",
                    "subreddit": subreddit,
                    "url": f"https://reddit.com{permalink}"
                })

    except Exception as e:
        print(f"[comments] Failed: {e}")

    return results
