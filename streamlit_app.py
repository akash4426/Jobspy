import streamlit as st
import pandas as pd
from jobspy import scrape_jobs
from datetime import datetime
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import re
import hashlib
import requests

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(
    page_title="GenAI Job Search Assistant",
    page_icon="Favicon1.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# Constants
# -------------------------------------------------
EMBED_DIM = 384

# -------------------------------------------------
# ATS Companies – Data / AI / ML (50+)
# -------------------------------------------------
ATS_COMPANIES = {
    "lever": [
        "scaleai","figma","canva","duolingo","webflow","postman","posthog",
        "segment","plaid","brex","shopify","algolia","datarobot","paxos",
        "supabase","vercel","linear","netlify","airbyte","fivetran",
        "rudderstack","montecarlodata","weightsandbiases","cohere",
        "stabilityai","cerebras","perplexityai","huggingface"
    ],
    "greenhouse": [
        "databricks","snowflake","datadog","airbnb","uber","lyft",
        "dropbox","twilio","github","elastic","cloudflare","mongodb",
        "palantir","pinterest","spotify","reddit","zoom","square",
        "hashicorp","gitlab","digitalocean","openai","anthropic",
        "amplitude","mixpanel"
    ]
}

# -------------------------------------------------
# Load Model
# -------------------------------------------------
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_model()

# -------------------------------------------------
# Utility Functions
# -------------------------------------------------
def clean_html(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_resume_text(pdf_file):
    reader = PdfReader(pdf_file)
    return " ".join(page.extract_text() or "" for page in reader.pages)

def determine_country(location_text):
    loc = str(location_text).lower()
    for k, v in {
        "india": "India", "canada": "Canada", "uk": "UK",
        "united kingdom": "UK", "australia": "Australia",
        "germany": "Germany", "france": "France", "singapore": "Singapore"
    }.items():
        if k in loc:
            return v
    return "USA"

# -------------------------------------------------
# ATS Fetchers (SAFE)
# -------------------------------------------------
def fetch_lever_jobs(company):
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        return [{
            "title": j.get("text"),
            "company": company.title(),
            "location": j.get("categories", {}).get("location", ""),
            "description": clean_html(j.get("description", "")),
            "job_url": j.get("hostedUrl"),
            "source": "Lever"
        } for j in r.json()]
    except Exception:
        return []

def fetch_greenhouse_jobs(company):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        return [{
            "title": j.get("title"),
            "company": company.title(),
            "location": j.get("location", {}).get("name", ""),
            "description": clean_html(j.get("content", "")),
            "job_url": j.get("absolute_url"),
            "source": "Greenhouse"
        } for j in r.json().get("jobs", [])]
    except Exception:
        return []

def fetch_all_ats_jobs():
    jobs = []
    for c in ATS_COMPANIES["lever"]:
        jobs.extend(fetch_lever_jobs(c))
    for c in ATS_COMPANIES["greenhouse"]:
        jobs.extend(fetch_greenhouse_jobs(c))
    return pd.DataFrame(jobs)

# -------------------------------------------------
# Deduplication (Single-run only)
# -------------------------------------------------
def job_fingerprint(row):
    key = f"{row.get('title','')}{row.get('company','')}{row.get('location','')}".lower()
    return hashlib.md5(key.encode()).hexdigest()

# -------------------------------------------------
# FAISS RAG Ranking (DEFENSIVE)
# -------------------------------------------------
def chunk_text(text, size=300):
    words = clean_html(text).split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]

def rank_jobs_with_rag(resume_text, df):
    if not resume_text or df.empty:
        df["match_score"] = 0
        return df

    chunks, mapping = [], []
    for idx, row in df.iterrows():
        for ch in chunk_text(row["description"]):
            if ch.strip():
                chunks.append(ch)
                mapping.append(idx)

    if not chunks:
        df["match_score"] = 0
        return df

    emb = model.encode(chunks, show_progress_bar=False)
    faiss.normalize_L2(emb)
    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(emb)

    r_emb = model.encode([resume_text])
    faiss.normalize_L2(r_emb)

    scores, idxs = index.search(r_emb, min(20, len(chunks)))

    job_scores = {}
    for s, i in zip(scores[0], idxs[0]):
        job_scores[mapping[i]] = max(job_scores.get(mapping[i], 0), s)

    df["match_score"] = df.index.map(lambda i: round(job_scores.get(i, 0) * 100, 2))
    return df.sort_values("match_score", ascending=False)

# -------------------------------------------------
# UI
# -------------------------------------------------
st.markdown("<h1 style='text-align:center'>GenAI Job Search Assistant</h1>", unsafe_allow_html=True)

with st.sidebar:
    job_role = st.text_input(placeholder="e.g., Data Scientist, ML Engineer", label="Job Role")
    location = st.text_input(placeholder="e.g., Hyderabad, Remote", label="Location")
    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    results = st.slider("Results", 10, 50, 25)
    search = st.button("Search Jobs", use_container_width=True)

# -------------------------------------------------
# Main Logic
# -------------------------------------------------
if search:
    with st.spinner(f"Fetching {job_role} roles from Job Boards..."):

        ats_df = fetch_all_ats_jobs()
        ats_df = ats_df[ats_df["title"].str.contains(job_role, case=False, na=False)]

        jobspy_df = scrape_jobs(
            site_name=["indeed", "linkedin"],
            search_term=job_role,
            location=location,
            results_wanted=results,
            hours_old=48,
            country_indeed=determine_country(location)
        )

        if not jobspy_df.empty:
            jobspy_df["source"] = "JobBoard"

        jobs_df = pd.concat([ats_df, jobspy_df], ignore_index=True)
        jobs_df["description"] = jobs_df["description"].fillna("")

        # Dedup within this run
        jobs_df["job_id"] = jobs_df.apply(job_fingerprint, axis=1)
        jobs_df = jobs_df.drop_duplicates("job_id")

        resume_text = extract_resume_text(resume_file) if resume_file else None
        jobs_df = rank_jobs_with_rag(resume_text, jobs_df)

        st.markdown(f"### Jobs Found: {len(jobs_df)}")

        for _, r in jobs_df.iterrows():
            st.markdown(
                f"""
                **{r['title']}**  
                {r['company']} — {r['location']}  
                Source: {r['source']}  
                Match Score: {r.get('match_score',0)}%  
                [Apply here]({r['job_url']})
                ---
                """
            )

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown("---")
st.markdown("<p style='text-align:center'>Built by Akash Karri | GenAI Job Search</p>", unsafe_allow_html=True)
