import requests
import time
import random
import re
from urllib.parse import quote, urlencode
from bs4 import BeautifulSoup

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
    }


def fetch_reddit_posts(keyword: str, limit: int = 100) -> list[dict]:
    posts = []
    reddit_urls = _duckduckgo_search_reddit(keyword, num_results=20)

    if not reddit_urls:
        return []

    for permalink in reddit_urls[:20]:
        thread_posts = _fetch_thread(permalink)
        posts.extend(thread_posts)
        time.sleep(0.6)
        if len(posts) >= limit:
            break

    return posts[:limit]


def _duckduckgo_search_reddit(keyword: str, num_results: int = 20) -> list[str]:
    """Search DuckDuckGo for Reddit threads — no bot protection, works on all servers."""
    permalinks = []

    queries = [
        f"site:reddit.com {keyword} problem",
        f"site:reddit.com {keyword} frustrated annoying",
        f"site:reddit.com {keyword} hate difficult",
    ]

    for query in queries:
        try:
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query, "kl": "us-en"}

            resp = requests.post(
                url,
                data=data,
                headers=_get_headers(),
                timeout=15
            )

            if resp.status_code != 200:
                print(f"[ddg] Status {resp.status_code}")
                time.sleep(1)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract all links from DDG results
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                # Find Reddit comment/post URLs
                match = re.search(
                    r'reddit\.com(/r/[^"&\s<>?#]+/comments/[^"&\s<>?#/]+(?:/[^"&\s<>?#/]+)?)',
                    href
                )
                if match:
                    clean = match.group(1).rstrip("/")
                    if clean not in permalinks:
                        permalinks.append(clean)

            time.sleep(1.5)

            if len(permalinks) >= num_results:
                break

        except Exception as e:
            print(f"[ddg] Search failed: {e}")
            continue

    print(f"[ddg] Found {len(permalinks)} Reddit URLs: {permalinks[:5]}")
    return permalinks[:num_results]


def _fetch_thread(permalink: str) -> list[dict]:
    """Fetch a Reddit thread's post + comments via JSON."""
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

        # Post itself
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

        # Comments
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
