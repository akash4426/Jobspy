import streamlit as st
import pandas as pd
from jobspy import scrape_jobs
from datetime import datetime
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import re
import hashlib
import os

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
SEEN_JOBS_FILE = "seen_jobs.csv"

# -------------------------------------------------
# Load Model (Cached)
# -------------------------------------------------
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_model()

# -------------------------------------------------
# Embedding Cache
# -------------------------------------------------
@st.cache_data(show_spinner=False)
def embed_texts(texts):
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    faiss.normalize_L2(embeddings)
    return embeddings

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
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def determine_country(location_text):
    loc = str(location_text).lower()
    mapping = {
        "india": "India",
        "canada": "Canada",
        "uk": "UK",
        "united kingdom": "UK",
        "australia": "Australia",
        "germany": "Germany",
        "france": "France",
        "singapore": "Singapore"
    }
    for k, v in mapping.items():
        if k in loc:
            return v
    return "USA"

# -------------------------------------------------
# Deduplication
# -------------------------------------------------
def job_fingerprint(row):
    base = (
        str(row.get("title", "")).lower().strip() +
        str(row.get("company", "")).lower().strip() +
        str(row.get("location", "")).lower().strip()
    )
    return hashlib.md5(base.encode()).hexdigest()

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        return set(pd.read_csv(SEEN_JOBS_FILE)["job_id"])
    return set()

def save_seen_jobs(job_ids):
    pd.DataFrame({"job_id": list(job_ids)}).to_csv(SEEN_JOBS_FILE, index=False)

# -------------------------------------------------
# Freshness Heuristic
# -------------------------------------------------
def infer_posted_days(text):
    if not isinstance(text, str):
        return None
    text = text.lower()
    if "today" in text or "just posted" in text:
        return 0
    match = re.search(r"(\d+)\s+day", text)
    return int(match.group(1)) if match else None

# -------------------------------------------------
# Experience Filter
# -------------------------------------------------
def filter_by_experience(df, level):
    if level == "All Levels":
        return df

    keywords = {
        "Internship": ["intern", "internship", "trainee", "student"],
        "Entry Level": ["entry", "junior", "associate", "graduate", "fresher"],
        "Mid Level": ["mid", "intermediate", "2+", "3+"],
        "Senior Level": ["senior", "lead", "principal", "staff", "architect"]
    }.get(level, [])

    pattern = "|".join(keywords)
    return df[
        df["title"].str.lower().str.contains(pattern, na=False) |
        df["description"].str.lower().str.contains(pattern, na=False)
    ]

# -------------------------------------------------
# FAISS + Weighted RAG Ranking
# -------------------------------------------------
def chunk_text(text, size=300):
    words = clean_html(text).split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]

def build_faiss_index(chunks):
    embeddings = embed_texts(chunks)
    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(embeddings)
    return index

def rank_jobs_with_rag(resume_text, df, top_k=20):
    df["clean_desc"] = df["description"].apply(clean_html)
    df["clean_title"] = df["title"].fillna("").str.lower()

    chunks, mapping = [], []

    for idx, row in df.iterrows():
        chunks.append(row["clean_title"])
        mapping.append((idx, 1.5))  # title weight

        for ch in chunk_text(row["clean_desc"]):
            chunks.append(ch)
            mapping.append((idx, 1.0))

    index = build_faiss_index(chunks)
    resume_vec = embed_texts([resume_text])

    scores, indices = index.search(resume_vec, min(top_k, len(chunks)))

    job_scores = {}
    for score, i in zip(scores[0], indices[0]):
        job_idx, weight = mapping[i]
        job_scores[job_idx] = max(job_scores.get(job_idx, 0), score * weight)

    df["match_score"] = df.index.map(
        lambda i: round(job_scores.get(i, 0) * 100, 2)
    )
    return df.sort_values("match_score", ascending=False)

def generate_match_reason(resume, desc):
    r = set(clean_html(resume).lower().split())
    d = set(clean_html(desc).lower().split())
    return ", ".join(list(r & d)[:5])

# -------------------------------------------------
# UI Header
# -------------------------------------------------
st.markdown("<h1 style='text-align:center'>GenAI Job Search Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center'>FAISS + RAG | Smart Dedup | Internship-Ready</p>", unsafe_allow_html=True)

# -------------------------------------------------
# Sidebar
# -------------------------------------------------
with st.sidebar:
    job_role = st.text_input("Job Title")
    location = st.text_input("Location")
    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    results_wanted = st.slider("Results", 5, 50, 15, 5)
    experience = st.selectbox(
        "Experience Level",
        ["All Levels", "Internship", "Entry Level", "Mid Level", "Senior Level"]
    )
    country_override = st.selectbox(
        "Country",
        ["Auto-detect", "USA", "India", "Canada", "UK", "Australia", "Germany", "France", "Singapore"]
    )
    search = st.button("Search Jobs", use_container_width=True)

# -------------------------------------------------
# Main Logic
# -------------------------------------------------
if search:
    if not job_role or not location:
        st.warning("Please enter Job Title and Location.")
    else:
        resume_text = None  # 🔥 CRITICAL FIX

        with st.spinner("Fetching and ranking jobs..."):
            country = country_override if country_override != "Auto-detect" else determine_country(location)

            jobs_df = scrape_jobs(
                site_name=["indeed", "linkedin"],
                search_term=job_role,
                location=location,
                results_wanted=results_wanted,
                hours_old=48,
                country_indeed=country
            )

            if jobs_df.empty:
                st.info("No jobs found.")
            else:
                jobs_df["description"] = jobs_df["description"].fillna("")

                jobs_df = filter_by_experience(jobs_df, experience)

                jobs_df["job_id"] = jobs_df.apply(job_fingerprint, axis=1)
                seen = load_seen_jobs()
                jobs_df = jobs_df[~jobs_df["job_id"].isin(seen)]

                jobs_df["posted_days"] = jobs_df["description"].apply(infer_posted_days)
                jobs_df = jobs_df[
                    (jobs_df["posted_days"].isna()) | (jobs_df["posted_days"] <= 3)
                ]

                if resume_file:
                    resume_text = extract_resume_text(resume_file)
                    if resume_text:
                        jobs_df = rank_jobs_with_rag(resume_text, jobs_df)

                save_seen_jobs(seen.union(set(jobs_df["job_id"])))

                st.markdown(f"### Jobs Found: {len(jobs_df)}")

                for _, row in jobs_df.iterrows():
                    st.markdown(
                        f"""
                        <div style="background:#0e1117;padding:1.5rem;border-radius:12px;margin-bottom:1rem">
                            <a href="{row.get('job_url','#')}" target="_blank"
                               style="color:#4DA6FF;font-size:1.1rem;font-weight:700">
                                {row.get('title')}
                            </a>
                            <div style="color:Black;font-size:1rem;font-weight:500">
                                {row.get('company')} — {row.get('location')}
                            </div>
                            <div style="color:Black;font-size:1rem;font-weight:500">
                                Match Score: {row.get('match_score', 0)}%
                            </div>
                            <div style="color:gray;font-size:0.9rem">
                                {f"Matched on: {generate_match_reason(resume_text, row['description'])}"
                                 if resume_text else ""}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                st.download_button(
                    "Download Results (CSV)",
                    jobs_df.to_csv(index=False).encode("utf-8"),
                    f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown("---")
st.markdown("<p style='text-align:center'>Built by Akash Karri | GenAI + FAISS</p>", unsafe_allow_html=True)
