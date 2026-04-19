import os
import json
import time
import streamlit as st
from groq import Groq

def analyze_complaints(posts: list[dict]) -> list[dict]:
    """
    Detect complaints from cleaned Reddit posts using Groq AI.
    Returns only posts classified as complaints, with extracted pain point.
    """
    api_key = _get_api_key()
    if not api_key:
        st.error("Groq API key not found. Add it to .streamlit/secrets.toml")
        return []

    client = Groq(api_key=api_key)

    # Send ALL posts to Groq — no pre-filter (RSS content is already complaint-heavy)
    # Limit to 40 posts max to stay within free tier rate limits
    posts_to_analyze = posts[:40]
    print(f"[analyze] Sending {len(posts_to_analyze)} posts to Groq")

    complaints = []
    batch_size = 5

    for i in range(0, len(posts_to_analyze), batch_size):
        batch = posts_to_analyze[i:i + batch_size]
        batch_results = _analyze_batch(client, batch)
        complaints.extend(batch_results)
        time.sleep(0.5)

    print(f"[analyze] Found {len(complaints)} complaints")
    return complaints


def _get_api_key() -> str | None:
    """Get Groq API key from Streamlit secrets or environment."""
    try:
        key = st.secrets["GROQ_API_KEY"]
        print(f"[analyze] Got API key: {key[:8]}...")
        return key
    except Exception as e:
        print(f"[analyze] secrets failed: {e}")
        return os.environ.get("GROQ_API_KEY")


def _analyze_batch(client: Groq, posts: list[dict]) -> list[dict]:
    """Send a batch of posts to Groq for complaint classification."""
    complaints = []

    for post in posts:
        text = post["text"][:800]

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
- pain_point should be specific and actionable"""

        try:
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.1
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()

            result = json.loads(raw)

            if result.get("is_complaint") and result.get("pain_point"):
                complaints.append({
                    **post,
                    "pain_point": result["pain_point"]
                })

        except json.JSONDecodeError as e:
            print(f"[analyze] JSON parse failed: {e}")
            continue
        except Exception as e:
            print(f"[analyze] Groq call failed: {e}")
            continue

    return complaints
