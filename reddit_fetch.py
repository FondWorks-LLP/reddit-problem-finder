import requests
import time
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

def fetch_reddit_posts(keyword: str, limit: int = 100) -> list[dict]:
    posts = []
    raw_posts = _search_reddit(keyword)

    if not raw_posts:
        return []

    for post_obj in raw_posts[:25]:
        post = post_obj.get("data", {})
        post_text = post.get("selftext", "").strip()
        post_title = post.get("title", "").strip()
        post_url = post.get("permalink", "")
        subreddit = post.get("subreddit", "")

        combined = f"{post_title}. {post_text}".strip()
        if combined and combined != ".":
            posts.append({
                "text": combined,
                "source": "post",
                "subreddit": subreddit,
                "url": f"https://reddit.com{post_url}"
            })

        comments = _fetch_comments(post_url)
        posts.extend(comments)
        time.sleep(0.8)

        if len(posts) >= limit:
            break

    return posts[:limit]


def _search_reddit(keyword: str) -> list:
    urls_to_try = [
        f"https://old.reddit.com/search.json?q={requests.utils.quote(keyword)}&sort=relevance&t=year&limit=50",
        f"https://www.reddit.com/search.json?q={requests.utils.quote(keyword)}&sort=new&limit=50",
        f"https://www.reddit.com/search.json?q={requests.utils.quote(keyword)}&sort=top&t=month&limit=50",
    ]

    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=_get_headers(), timeout=20, allow_redirects=True)
            if resp.status_code == 200:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                if children:
                    return children
            elif resp.status_code == 429:
                time.sleep(2)
                continue
        except Exception as e:
            print(f"[reddit_fetch] URL failed {url}: {e}")
            continue

    return []


def _fetch_comments(permalink: str) -> list[dict]:
    comments = []
    if not permalink:
        return comments

    url = f"https://old.reddit.com{permalink}.json?limit=8&sort=top"

    try:
        resp = requests.get(url, headers=_get_headers(), timeout=12, allow_redirects=True)
        if resp.status_code != 200:
            return comments

        data = resp.json()
        if len(data) < 2:
            return comments

        comment_listing = data[1].get("data", {}).get("children", [])
        subreddit = ""
        try:
            subreddit = data[0]["data"]["children"][0]["data"].get("subreddit", "")
        except Exception:
            pass

        for comment_obj in comment_listing[:6]:
            comment = comment_obj.get("data", {})
            body = comment.get("body", "").strip()
            if body and body not in ("[deleted]", "[removed]") and len(body) > 20:
                comments.append({
                    "text": body,
                    "source": "comment",
                    "subreddit": subreddit,
                    "url": f"https://reddit.com{permalink}"
                })

    except Exception as e:
        print(f"[reddit_fetch] Comment fetch failed: {e}")

    return comments
