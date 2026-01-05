import streamlit as st
import pandas as pd
from jobspy import scrape_jobs
from datetime import datetime
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
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
# Load ML Model (Cached)
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
        "singapore": "Singapore",
    }
    for k, v in mapping.items():
        if k in loc:
            return v
    return "USA"

# -------------------------------------------------
# Job Deduplication
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
    if match:
        return int(match.group(1))

    return None

# -------------------------------------------------
# Experience Level Filter (EXACT)
# -------------------------------------------------
def filter_by_experience(jobs_df, experience_level):
    if experience_level == "All Levels":
        return jobs_df

    title = jobs_df["title"].str.lower().fillna("")
    desc = jobs_df["description"].str.lower().fillna("")

    if experience_level == "Internship":
        keywords = ["intern", "internship", "trainee", "student"]

    elif experience_level == "Entry Level":
        keywords = ["entry", "junior", "associate", "graduate", "fresher"]

    elif experience_level == "Mid Level":
        keywords = ["mid", "intermediate", "ii", "2+", "3+"]

    elif experience_level == "Senior Level":
        keywords = ["senior", "lead", "principal", "staff", "architect"]

    pattern = "|".join(keywords)
    mask = title.str.contains(pattern) | desc.str.contains(pattern)
    return jobs_df[mask]

# -------------------------------------------------
# RAG Utilities
# -------------------------------------------------
def chunk_text(text, chunk_size=300):
    words = clean_html(text).split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

def build_faiss_index(text_chunks):
    embeddings = model.encode(text_chunks, show_progress_bar=False)
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(embeddings)
    return index

def rank_jobs_with_rag(resume_text, jobs_df, top_k=20):
    jobs_df["clean_description"] = jobs_df["description"].apply(clean_html)

    job_chunks, chunk_to_job = [], []

    for idx, desc in enumerate(jobs_df["clean_description"]):
        for ch in chunk_text(desc):
            job_chunks.append(ch)
            chunk_to_job.append(idx)

    if not job_chunks:
        jobs_df["match_score"] = 0
        return jobs_df

    index = build_faiss_index(job_chunks)

    resume_embedding = model.encode([resume_text])
    faiss.normalize_L2(resume_embedding)

    scores, indices = index.search(resume_embedding, min(top_k, len(job_chunks)))

    job_scores = {}
    for score, idx in zip(scores[0], indices[0]):
        job_id = chunk_to_job[idx]
        job_scores[job_id] = max(job_scores.get(job_id, 0), score)

    jobs_df["match_score"] = jobs_df.index.map(
        lambda i: round(job_scores.get(i, 0) * 100, 2)
    )

    return jobs_df.sort_values("match_score", ascending=False)

# -------------------------------------------------
# UI Header
# -------------------------------------------------
st.markdown("<h1 style='text-align:center'>GenAI-Powered Job Search Assistant</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;font-size:1.05rem'>FAISS + RAG | Deduplication | Internship Support</p>",
    unsafe_allow_html=True
)

# -------------------------------------------------
# Sidebar
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
# Main Logic
# -------------------------------------------------
if search_clicked:
    if not job_role or not location:
        st.warning("Please enter both Job Title and Location.")
    else:
        with st.spinner("Scraping, filtering, and ranking jobs..."):
            try:
                country = (
                    country_override
                    if country_override != "Auto-detect"
                    else determine_country(location)
                )

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
                    jobs_df["description"] = jobs_df["description"].fillna("").astype(str)

                    # Experience filtering (EXACT)
                    jobs_df = filter_by_experience(jobs_df, experience_level)

                    # Deduplication
                    jobs_df["job_id"] = jobs_df.apply(job_fingerprint, axis=1)
                    seen_jobs = load_seen_jobs()
                    jobs_df = jobs_df[~jobs_df["job_id"].isin(seen_jobs)]

                    # Freshness filter
                    jobs_df["posted_days"] = jobs_df["description"].apply(infer_posted_days)
                    jobs_df = jobs_df[
                        (jobs_df["posted_days"].isna()) | (jobs_df["posted_days"] <= 3)
                    ]

                    if jobs_df.empty:
                        st.info("Only duplicate or stale jobs were found.")
                    else:
                        save_seen_jobs(seen_jobs.union(set(jobs_df["job_id"])))

                        if resume_file:
                            resume_text = extract_resume_text(resume_file)
                            if resume_text:
                                jobs_df = rank_jobs_with_rag(resume_text, jobs_df)
                                st.success("Jobs ranked using FAISS-based RAG.")

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

                        csv = jobs_df.to_csv(index=False).encode("utf-8")
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

                        st.download_button(
                            "Download Results (CSV)",
                            csv,
                            f"job_results_{ts}.csv",
                            "text/csv",
                            use_container_width=True
                        )

            except Exception as e:
                st.error(f"Error: {str(e)}")
else:
    st.info("Enter details in the sidebar to start your job search.")

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown("---")
st.markdown(
    "<p style='text-align:center'>Built by Akash Karri | GenAI + FAISS Retrieval</p>",
    unsafe_allow_html=True
)