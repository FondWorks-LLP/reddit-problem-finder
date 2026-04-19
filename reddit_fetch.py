import requests
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (RedditProblemFinder/1.0)"
}

def fetch_reddit_posts(keyword: str, limit: int = 100) -> list[dict]:
    """
    Fetch Reddit posts + top comments for a keyword.
    Uses Reddit's public JSON endpoint — no API key required.
    """
    posts = []

    # ── Step 1: Search posts ──────────────────────────────────────────────────
    search_url = (
        f"https://www.reddit.com/search.json"
        f"?q={requests.utils.quote(keyword)}"
        f"&sort=relevance&t=year&limit=50&type=link"
    )

    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        raw_posts = data.get("data", {}).get("children", [])
    except Exception as e:
        print(f"[reddit_fetch] Search failed: {e}")
        return []

    # ── Step 2: For each post, grab post text + top comments ─────────────────
    for post_obj in raw_posts[:30]:  # limit to 30 posts to stay fast
        post = post_obj.get("data", {})

        post_text = post.get("selftext", "").strip()
        post_title = post.get("title", "").strip()
        post_url = post.get("permalink", "")
        subreddit = post.get("subreddit", "")

        # Add post itself
        combined = f"{post_title}. {post_text}".strip()
        if combined:
            posts.append({
                "text": combined,
                "source": "post",
                "subreddit": subreddit,
                "url": f"https://reddit.com{post_url}"
            })

        # Fetch top comments from this post
        comments = _fetch_comments(post_url)
        posts.extend(comments)

        time.sleep(0.5)  # polite delay to avoid rate limiting

        if len(posts) >= limit:
            break

    return posts[:limit]


def _fetch_comments(permalink: str) -> list[dict]:
    """Fetch top comments from a Reddit post."""
    comments = []

    if not permalink:
        return comments

    url = f"https://www.reddit.com{permalink}.json?limit=10&sort=top"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Comments are in index [1]
        if len(data) < 2:
            return comments

        comment_listing = data[1].get("data", {}).get("children", [])
        subreddit = data[0].get("data", {}).get("children", [{}])[0].get("data", {}).get("subreddit", "")

        for comment_obj in comment_listing[:5]:
            comment = comment_obj.get("data", {})
            body = comment.get("body", "").strip()

            if body and body != "[deleted]" and body != "[removed]":
                comments.append({
                    "text": body,
                    "source": "comment",
                    "subreddit": subreddit,
                    "url": f"https://reddit.com{permalink}"
                })

    except Exception as e:
        print(f"[reddit_fetch] Comment fetch failed for {permalink}: {e}")

    return comments
