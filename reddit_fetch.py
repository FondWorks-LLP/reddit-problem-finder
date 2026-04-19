import requests
import time
import random
import re
from urllib.parse import quote, urlencode

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/",
    }


def fetch_reddit_posts(keyword: str, limit: int = 100) -> list[dict]:
    """
    Fetch Reddit posts by searching Google for site:reddit.com results,
    then fetching each Reddit thread's JSON directly.
    No API key required. Works on cloud servers.
    """
    posts = []

    # Step 1: Get Reddit thread URLs via Google
    reddit_urls = _google_search_reddit(keyword, num_results=20)

    if not reddit_urls:
        return []

    # Step 2: Fetch each Reddit thread JSON
    for permalink in reddit_urls[:20]:
        thread_posts = _fetch_thread(permalink, keyword)
        posts.extend(thread_posts)
        time.sleep(0.6)

        if len(posts) >= limit:
            break

    return posts[:limit]


def _google_search_reddit(keyword: str, num_results: int = 20) -> list[str]:
    """
    Search Google for Reddit threads about the keyword.
    Returns list of Reddit permalinks.
    """
    permalinks = []

    queries = [
        f"site:reddit.com {keyword} problem",
        f"site:reddit.com {keyword} frustrated",
        f"site:reddit.com {keyword} hate",
    ]

    for query in queries:
        try:
            params = {
                "q": query,
                "num": 10,
                "hl": "en",
                "gl": "us",
            }
            url = f"https://www.google.com/search?{urlencode(params)}"

            resp = requests.get(url, headers=_get_headers(), timeout=15)

            if resp.status_code != 200:
                time.sleep(1)
                continue

            # Extract Reddit URLs from Google HTML
            found = re.findall(
                r'reddit\.com(/r/[^"&\s<>]+/comments/[^"&\s<>]+)',
                resp.text
            )

            for path in found:
                # Clean up the path
                clean = path.split("?")[0].rstrip("/")
                if clean not in permalinks:
                    permalinks.append(clean)

            time.sleep(1.2)  # be polite to Google

            if len(permalinks) >= num_results:
                break

        except Exception as e:
            print(f"[google_search] Failed: {e}")
            continue

    return permalinks[:num_results]


def _fetch_thread(permalink: str, keyword: str) -> list[dict]:
    """
    Fetch a single Reddit thread's post + comments via JSON.
    """
    results = []

    url = f"https://www.reddit.com{permalink}.json?limit=10&sort=top"

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

        if not data or len(data) < 1:
            return results

        # ── Post itself ───────────────────────────────────────────────────────
        try:
            post_data = data[0]["data"]["children"][0]["data"]
            title = post_data.get("title", "").strip()
            selftext = post_data.get("selftext", "").strip()
            subreddit = post_data.get("subreddit", "")

            combined = f"{title}. {selftext}".strip().rstrip(".")
            if combined and len(combined) > 20:
                results.append({
                    "text": combined,
                    "source": "post",
                    "subreddit": subreddit,
                    "url": f"https://reddit.com{permalink}"
                })
        except Exception:
            pass

        # ── Comments ──────────────────────────────────────────────────────────
        if len(data) >= 2:
            try:
                comments = data[1]["data"]["children"]
                subreddit = ""
                try:
                    subreddit = data[0]["data"]["children"][0]["data"].get("subreddit", "")
                except Exception:
                    pass

                for c in comments[:8]:
                    body = c.get("data", {}).get("body", "").strip()
                    if body and body not in ("[deleted]", "[removed]") and len(body) > 20:
                        results.append({
                            "text": body,
                            "source": "comment",
                            "subreddit": subreddit,
                            "url": f"https://reddit.com{permalink}"
                        })
            except Exception:
                pass

    except Exception as e:
        print(f"[fetch_thread] Failed for {permalink}: {e}")

    return results
