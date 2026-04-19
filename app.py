import streamlit as st
import pandas as pd
import plotly.express as px
from reddit_fetch import fetch_reddit_posts
from clean import clean_posts
from analyze import analyze_complaints
from cluster import cluster_complaints
import io

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Reddit Problem Finder",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: #0a0a0f;
    color: #e8e8f0;
}

h1, h2, h3 {
    font-family: 'Space Mono', monospace !important;
}

.hero-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.8rem;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.2;
    margin-bottom: 0.3rem;
}

.hero-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    color: #6b6b8a;
    margin-bottom: 2rem;
}

.accent { color: #ff4444; }

.metric-card {
    background: #13131f;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}

.metric-card h4 {
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    color: #6b6b8a;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 0 0 0.4rem 0;
}

.metric-card .value {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #ff4444;
}

.problem-card {
    background: #13131f;
    border: 1px solid #1e1e2e;
    border-left: 3px solid #ff4444;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.2s;
}

.problem-card:hover {
    border-left-color: #ff7777;
}

.problem-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 0.3rem;
}

.problem-count {
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    color: #ff4444;
    margin-bottom: 0.5rem;
}

.problem-quote {
    font-size: 0.85rem;
    color: #8888aa;
    font-style: italic;
    line-height: 1.5;
    border-left: 2px solid #1e1e2e;
    padding-left: 0.8rem;
    margin-top: 0.5rem;
}

.stTextInput > div > div > input {
    background: #13131f !important;
    border: 1px solid #1e1e2e !important;
    border-radius: 8px !important;
    color: #e8e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    padding: 0.8rem 1rem !important;
}

.stTextInput > div > div > input:focus {
    border-color: #ff4444 !important;
    box-shadow: 0 0 0 1px #ff444430 !important;
}

.stButton > button {
    background: #ff4444 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.9rem !important;
    font-weight: 700 !important;
    padding: 0.7rem 2rem !important;
    letter-spacing: 0.05em !important;
    transition: background 0.2s !important;
}

.stButton > button:hover {
    background: #cc3333 !important;
}

.stSpinner > div {
    border-top-color: #ff4444 !important;
}

div[data-testid="stStatusWidget"] { display: none; }

.divider {
    border: none;
    border-top: 1px solid #1e1e2e;
    margin: 2rem 0;
}

.tag {
    display: inline-block;
    background: #1e1e2e;
    color: #6b6b8a;
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    margin-right: 0.3rem;
    margin-bottom: 0.3rem;
}

.footer {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: #2a2a3a;
    text-align: center;
    margin-top: 4rem;
    padding-top: 1rem;
    border-top: 1px solid #1a1a2a;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-title">Reddit <span class="accent">Problem</span> Finder</div>
<div class="hero-sub">Surface real pain points from Reddit — before you build anything.</div>
""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Search Input ──────────────────────────────────────────────────────────────
col_input, col_btn = st.columns([5, 1])

with col_input:
    keyword = st.text_input(
        label="keyword",
        placeholder="e.g. freelancing, invoice software, gym tracking...",
        label_visibility="collapsed"
    )

with col_btn:
    search_clicked = st.button("SEARCH →")

# ── Example tags ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top: -0.5rem; margin-bottom: 1.5rem;">
    <span class="tag">freelancing</span>
    <span class="tag">saas tools</span>
    <span class="tag">remote work</span>
    <span class="tag">gym tracking</span>
    <span class="tag">meal planning</span>
    <span class="tag">student loans</span>
</div>
""", unsafe_allow_html=True)

# ── Pipeline ──────────────────────────────────────────────────────────────────
if search_clicked and keyword.strip():
    keyword = keyword.strip()

    progress_placeholder = st.empty()
    results_placeholder = st.container()

    with progress_placeholder:
        with st.status(f"Analyzing Reddit for **'{keyword}'**...", expanded=True) as status:

            st.write("📡 Fetching Reddit posts and comments...")
            raw_posts = fetch_reddit_posts(keyword, limit=100)

            if not raw_posts:
                st.error("No posts found. Try a different keyword.")
                st.stop()

            st.write(f"✅ Fetched {len(raw_posts)} posts")

            st.write("🧹 Cleaning and filtering text...")
            cleaned = clean_posts(raw_posts)
            st.write(f"✅ {len(cleaned)} posts after cleaning")

            st.write("🤖 Detecting complaints with AI...")
            complaints = analyze_complaints(cleaned)
            st.write(f"✅ {len(complaints)} complaints identified")

            if not complaints:
                st.warning("No complaints found for this keyword. Try something more specific.")
                st.stop()

            st.write("🔗 Clustering similar problems...")
            clusters = cluster_complaints(complaints)
            st.write(f"✅ {len(clusters)} problem clusters formed")

            status.update(label="✅ Analysis complete!", state="complete", expanded=False)

    # ── Metrics Row ───────────────────────────────────────────────────────────
    with results_placeholder:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Posts Fetched</h4>
                <div class="value">{len(raw_posts)}</div>
            </div>""", unsafe_allow_html=True)

        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Complaints Found</h4>
                <div class="value">{len(complaints)}</div>
            </div>""", unsafe_allow_html=True)

        with m3:
            pct = round(len(complaints) / len(cleaned) * 100) if cleaned else 0
            st.markdown(f"""
            <div class="metric-card">
                <h4>Complaint Rate</h4>
                <div class="value">{pct}%</div>
            </div>""", unsafe_allow_html=True)

        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Problem Clusters</h4>
                <div class="value">{len(clusters)}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Two column layout ─────────────────────────────────────────────────
        left_col, right_col = st.columns([1, 1])

        with left_col:
            st.markdown("### Top Problems")
            st.markdown("<br>", unsafe_allow_html=True)

            for i, cluster in enumerate(clusters[:8]):
                label = cluster.get("label", f"Problem {i+1}")
                count = cluster.get("count", 0)
                quotes = cluster.get("quotes", [])
                quote_text = quotes[0][:180] + "..." if quotes and len(quotes[0]) > 180 else (quotes[0] if quotes else "")

                st.markdown(f"""
                <div class="problem-card">
                    <div class="problem-label">#{i+1} — {label}</div>
                    <div class="problem-count">↑ {count} mentions</div>
                    {f'<div class="problem-quote">"{quote_text}"</div>' if quote_text else ''}
                </div>
                """, unsafe_allow_html=True)

        with right_col:
            st.markdown("### Frequency Chart")
            st.markdown("<br>", unsafe_allow_html=True)

            chart_data = pd.DataFrame([
                {"Problem": f"#{i+1} {c['label'][:30]}", "Mentions": c["count"]}
                for i, c in enumerate(clusters[:8])
            ])

            fig = px.bar(
                chart_data,
                x="Mentions",
                y="Problem",
                orientation="h",
                color="Mentions",
                color_continuous_scale=["#1e1e2e", "#ff4444"],
            )

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Space Mono", color="#e8e8f0", size=11),
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
                yaxis=dict(
                    autorange="reversed",
                    tickfont=dict(size=10),
                    gridcolor="#1e1e2e"
                ),
                xaxis=dict(gridcolor="#1e1e2e"),
                height=380
            )

            st.plotly_chart(fig, use_container_width=True)

        # ── Export ────────────────────────────────────────────────────────────
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        export_rows = []
        for i, cluster in enumerate(clusters):
            for quote in cluster.get("quotes", []):
                export_rows.append({
                    "rank": i + 1,
                    "problem_label": cluster.get("label", ""),
                    "mention_count": cluster.get("count", 0),
                    "example_quote": quote,
                    "keyword": keyword
                })

        df_export = pd.DataFrame(export_rows)
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False)

        col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 4])
        with col_exp1:
            st.download_button(
                label="⬇ EXPORT CSV",
                data=csv_buffer.getvalue(),
                file_name=f"reddit_problems_{keyword.replace(' ', '_')}.csv",
                mime="text/csv"
            )

elif search_clicked and not keyword.strip():
    st.warning("Please enter a keyword to search.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    REDDIT PROBLEM FINDER — built with Streamlit + Groq AI — for validated idea discovery
</div>
""", unsafe_allow_html=True)
