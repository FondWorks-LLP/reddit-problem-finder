import os
import json
import time
import streamlit as st
from groq import Groq

# ── Complaint keywords for fast pre-filter (saves API calls) ─────────────────
COMPLAINT_SIGNALS = [
    "hate", "annoying", "frustrated", "frustrating", "terrible", "awful",
    "difficult", "expensive", "overpriced", "broken", "useless", "waste",
    "no one", "nobody", "can't", "cannot", "doesn't work", "doesn't have",
    "missing", "lack", "lacking", "wish", "why is", "why can't", "why don't",
    "problem", "issue", "bug", "broken", "tired of", "sick of", "fed up",
    "impossible", "horrible", "worst", "sucks", "garbage", "rubbish",
    "need a way", "there's no", "there is no", "why isn't", "hard to",
    "struggle", "struggling"
]

def analyze_complaints(posts: list[dict]) -> list[dict]:
    """
    Detect complaints from cleaned Reddit posts using Groq AI.
    Returns only posts classified as complaints, with extracted pain point.
    """
    # ── Get Groq client ───────────────────────────────────────────────────────
    api_key = _get_api_key()
    if not api_key:
        st.error("Groq API key not found. Add it to .streamlit/secrets.toml")
        return []

    client = Groq(api_key=api_key)

    # ── Pre-filter with keywords (reduce API calls by ~50%) ──────────────────
    pre_filtered = _keyword_prefilter(posts)

    complaints = []
    batch_size = 5  # process in small batches to stay within rate limits

    for i in range(0, len(pre_filtered), batch_size):
        batch = pre_filtered[i:i + batch_size]
        batch_results = _analyze_batch(client, batch)
        complaints.extend(batch_results)
        time.sleep(0.3)  # polite delay

    return complaints


def _get_api_key() -> str | None:
    """Get Groq API key from Streamlit secrets or environment."""
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.environ.get("GROQ_API_KEY")


def _keyword_prefilter(posts: list[dict]) -> list[dict]:
    """
    Fast keyword pre-filter — only send likely complaints to AI.
    Reduces Groq API calls significantly.
    """
    filtered = []
    for post in posts:
        text_lower = post["text"].lower()
        if any(signal in text_lower for signal in COMPLAINT_SIGNALS):
            filtered.append(post)
    return filtered


def _analyze_batch(client: Groq, posts: list[dict]) -> list[dict]:
    """Send a batch of posts to Groq for complaint classification."""
    complaints = []

    for post in posts:
        text = post["text"][:800]  # truncate to save tokens

        prompt = f"""Analyze this Reddit text and determine if it expresses a real complaint, frustration, or unmet need.

Text: "{text}"

Respond ONLY with valid JSON in this exact format:
{{
  "is_complaint": true or false,
  "pain_point": "one sentence summary of the core problem (empty string if not a complaint)"
}}

Rules:
- is_complaint = true only for genuine frustrations, problems, or unmet needs
- General opinions, stories, or advice are NOT complaints
- pain_point should be specific and actionable (what problem is this person facing?)"""

        try:
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.1
            )

            raw = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            raw = raw.replace("```json", "").replace("```", "").strip()

            result = json.loads(raw)

            if result.get("is_complaint") and result.get("pain_point"):
                complaints.append({
                    **post,
                    "pain_point": result["pain_point"]
                })

        except json.JSONDecodeError:
            # If AI returns malformed JSON, skip this post
            continue
        except Exception as e:
            print(f"[analyze] Groq call failed: {e}")
            continue

    return complaints
