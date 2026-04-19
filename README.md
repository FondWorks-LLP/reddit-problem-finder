# Reddit Problem Finder 🔍

Surface real pain points from Reddit — before you build anything.

## Stack
- **UI**: Streamlit
- **Data**: Reddit public JSON (no API key needed)
- **AI**: Groq API (llama3-8b) — free tier
- **Clustering**: TF-IDF + KMeans (scikit-learn)

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/reddit-problem-finder
cd reddit-problem-finder
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add your Groq API key
Create `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "your_groq_api_key_here"
```
Get a free key at: https://console.groq.com

### 4. Run locally
```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push repo to GitHub
2. Go to https://share.streamlit.io
3. Connect your GitHub repo
4. Add `GROQ_API_KEY` in the Secrets section (Settings → Secrets)
5. Deploy

## File Structure
```
reddit-problem-finder/
├── app.py              # Streamlit UI
├── reddit_fetch.py     # Reddit public JSON fetcher
├── clean.py            # Text cleaning pipeline
├── analyze.py          # Groq AI complaint classifier
├── cluster.py          # TF-IDF + KMeans clustering
├── requirements.txt
└── .streamlit/
    └── secrets.toml    # API keys (never commit this)
```

## Pipeline
```
Keyword Input
    → Fetch Reddit posts + comments (public JSON)
    → Clean text (remove spam, URLs, short posts)
    → AI classify complaints (Groq llama3-8b)
    → Cluster similar complaints (TF-IDF + KMeans)
    → Dashboard with top problems + CSV export
```
