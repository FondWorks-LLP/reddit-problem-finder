import re

# Minimum word count to keep a post
MIN_WORDS = 12

# Spam/bot patterns to remove
SPAM_PATTERNS = [
    r"i am a bot",
    r"automoderator",
    r"this action was performed",
    r"if you have any questions.*message the moderators",
    r"^\s*\[deleted\]\s*$",
    r"^\s*\[removed\]\s*$",
    r"http\S+",           # URLs
    r"www\.\S+",          # www links
]

def clean_posts(posts: list[dict]) -> list[dict]:
    """
    Clean raw Reddit posts.
    - Remove spam, bots, deleted posts
    - Remove URLs and special characters
    - Filter by minimum length
    - Deduplicate
    """
    cleaned = []
    seen_texts = set()

    for post in posts:
        text = post.get("text", "")

        # Basic cleanup
        text = _clean_text(text)

        # Skip if empty or too short
        if not text or len(text.split()) < MIN_WORDS:
            continue

        # Skip spam/bot content
        if _is_spam(text):
            continue

        # Deduplicate (fuzzy: first 80 chars as key)
        dedup_key = text[:80].lower().strip()
        if dedup_key in seen_texts:
            continue
        seen_texts.add(dedup_key)

        cleaned.append({
            **post,
            "text": text
        })

    return cleaned


def _clean_text(text: str) -> str:
    """Clean a single text string."""
    if not text:
        return ""

    # Remove URLs
    text = re.sub(r"http\S+|www\.\S+", "", text)

    # Remove Reddit formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)        # italic
    text = re.sub(r"~~(.+?)~~", r"\1", text)        # strikethrough
    text = re.sub(r"`(.+?)`", r"\1", text)          # code
    text = re.sub(r"&gt;.*", "", text)              # quotes
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)

    # Remove excessive whitespace / newlines
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)

    # Remove non-ASCII (emojis, special chars) — keep standard punctuation
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    return text.strip()


def _is_spam(text: str) -> bool:
    """Return True if the text matches any spam pattern."""
    text_lower = text.lower()
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False
