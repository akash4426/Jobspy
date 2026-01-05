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
# Page Configuration (UNCHANGED)
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
# Load Model (UNCHANGED)
# -------------------------------------------------
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_model()

# -------------------------------------------------
# Utility Functions (UNCHANGED)
# -------------------------------------------------
def clean_html(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_resume_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def determine_country(location_text):
    loc = str(location_text).lower()
    mapping = {
        "india": "India", "canada": "Canada", "uk": "UK",
        "united kingdom": "UK", "australia": "Australia",
        "germany": "Germany", "france": "France", "singapore": "Singapore"
    }
    for k, v in mapping.items():
        if k in loc:
            return v
    return "USA"

# -------------------------------------------------
# ATS Fetchers (NEW – BACKEND ONLY)
# -------------------------------------------------
def fetch_lever_jobs(company):
    try:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
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
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
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
# Deduplication (IN-MEMORY ONLY)
# -------------------------------------------------
def job_fingerprint(row):
    base = (
        str(row.get("title","")) +
        str(row.get("company","")) +
        str(row.get("location",""))
    ).lower()
    return hashlib.md5(base.encode()).hexdigest()

# -------------------------------------------------
# RAG Utilities (UNCHANGED LOGIC)
# -------------------------------------------------
def chunk_text(text, chunk_size=300):
    words = clean_html(text).split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def rank_jobs_with_rag(resume_text, jobs_df):
    if not resume_text or jobs_df.empty:
        jobs_df["match_score"] = 0
        return jobs_df

    chunks, mapping = [], []

    for idx, row in jobs_df.iterrows():
        for ch in chunk_text(row["description"]):
            if ch.strip():
                chunks.append(ch)
                mapping.append(idx)

    if not chunks:
        jobs_df["match_score"] = 0
        return jobs_df

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

    jobs_df["match_score"] = jobs_df.index.map(
        lambda i: round(job_scores.get(i, 0)*100, 2)
    )

    return jobs_df.sort_values("match_score", ascending=False)

# -------------------------------------------------
# UI Header (UNCHANGED)
# -------------------------------------------------
st.markdown("<h1 style='text-align:center'>GenAI-Powered Job Search Assistant</h1>", unsafe_allow_html=True)

# -------------------------------------------------
# Sidebar (UNCHANGED)
# -------------------------------------------------
with st.sidebar:
    st.markdown("### Search Configuration")
    job_role = st.text_input("Job Title", placeholder="e.g., AI Engineer")
    location = st.text_input("Location", placeholder="e.g., Visakhapatnam, India")
    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

    st.markdown("---")
    results_wanted = st.slider("Number of Results", 5, 50, 15, step=5)

    experience_level = st.selectbox(
        "Experience Level",
        ["All Levels", "Internship", "Entry Level", "Mid Level", "Senior Level"]
    )

    country_override = st.selectbox(
        "Country",
        ["Auto-detect", "USA", "India", "Canada", "UK", "Australia", "Germany", "France", "Singapore"]
    )

    search_clicked = st.button("Search Jobs", use_container_width=True)

# -------------------------------------------------
# Main Logic (UI SAME, BACKEND ENHANCED)
# -------------------------------------------------
if search_clicked:
    if not job_role or not location:
        st.warning("Please enter both Job Title and Location.")
    else:
        with st.spinner("Scraping, filtering, and ranking jobs..."):

            country = country_override if country_override != "Auto-detect" else determine_country(location)

            # ATS jobs
            ats_df = fetch_all_ats_jobs()
            if not ats_df.empty:
                ats_df = ats_df[ats_df["title"].str.contains(job_role, case=False, na=False)]

            # JobSpy jobs
            jobspy_df = scrape_jobs(
                site_name=["indeed", "linkedin"],
                search_term=job_role,
                location=location,
                results_wanted=results_wanted,
                hours_old=48,
                country_indeed=country
            )

            if not jobspy_df.empty:
                jobspy_df["source"] = "JobBoard"

            jobs_df = pd.concat([ats_df, jobspy_df], ignore_index=True)
            jobs_df["description"] = jobs_df["description"].fillna("")

            # Dedup in-memory
            jobs_df["job_id"] = jobs_df.apply(job_fingerprint, axis=1)
            jobs_df = jobs_df.drop_duplicates("job_id")

            # RAG ranking
            resume_text = extract_resume_text(resume_file) if resume_file else None
            jobs_df = rank_jobs_with_rag(resume_text, jobs_df)

            st.markdown(f"### Jobs Found: {len(jobs_df)}")

            for _, row in jobs_df.iterrows():
                st.markdown(
                    f"""
                    <div style="background:black;padding:1.5rem;
                    border-radius:12px;margin-bottom:1rem;
                    box-shadow:0 4px 12px rgba(0,0,0,0.08)">
                        <a href="{row.get('job_url', '#')}" target="_blank"
                           style="font-size:1.1rem;font-weight:700;color:#4DA6FF">
                            {row.get('title', 'N/A')}
                        </a>
                        <div style="color:white">{row.get('company', 'N/A')} — {row.get('location', 'N/A')}</div>
                        <div style="color:white;font-weight:600">
                            Match Score: {row.get('match_score', 0)}%
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

else:
    st.info("Enter details in the sidebar to start your job search.")

# -------------------------------------------------
# Footer (UNCHANGED)
# -------------------------------------------------
st.markdown("---")
st.markdown(
    "<p style='text-align:center'>Built by Akash Karri | GenAI + FAISS Retrieval</p>",
    unsafe_allow_html=True
)
