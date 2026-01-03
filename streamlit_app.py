import streamlit as st
import pandas as pd
from jobspy import scrape_jobs
from datetime import datetime
from pypdf import PdfReader

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import faiss
import numpy as np

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(
    page_title="GenAI Job Search Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# Load ML Model (Cached)
# -------------------------------------------------
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_model()
EMBED_DIM = 384  # for all-MiniLM-L6-v2

# -------------------------------------------------
# Helper Functions
# -------------------------------------------------
def extract_resume_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def determine_country(location_text):
    loc = location_text.lower()
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
# RAG: Chunking + Vector Index
# -------------------------------------------------
def chunk_text(text, chunk_size=300):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks

def build_faiss_index(text_chunks):
    embeddings = model.encode(text_chunks, show_progress_bar=False)
    index = faiss.IndexFlatIP(EMBED_DIM)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    return index, embeddings

def rank_jobs_with_rag(resume_text, jobs_df, top_k=20):
    job_texts = jobs_df["description"].fillna("").tolist()

    # Create chunks for retrieval
    job_chunks = []
    chunk_to_job = []

    for idx, text in enumerate(job_texts):
        chunks = chunk_text(text)
        for ch in chunks:
            job_chunks.append(ch)
            chunk_to_job.append(idx)

    if not job_chunks:
        return jobs_df

    index, _ = build_faiss_index(job_chunks)

    resume_embedding = model.encode([resume_text])
    faiss.normalize_L2(resume_embedding)

    scores, indices = index.search(resume_embedding, k=min(top_k, len(job_chunks)))

    job_scores = {}
    for score, idx in zip(scores[0], indices[0]):
        job_id = chunk_to_job[idx]
        job_scores[job_id] = max(job_scores.get(job_id, 0), score)

    jobs_df["match_score"] = jobs_df.index.map(
        lambda i: round(job_scores.get(i, 0) * 100, 2)
    )

    return jobs_df.sort_values("match_score", ascending=False)

# -------------------------------------------------
# Simple Explanation Generator (Interview-Safe)
# -------------------------------------------------
def generate_match_reason(resume_text, job_desc):
    resume_keywords = set(resume_text.lower().split()[:50])
    job_keywords = set(job_desc.lower().split())
    overlap = resume_keywords.intersection(job_keywords)

    if overlap:
        return f"Matches skills like: {', '.join(list(overlap)[:5])}"
    return "Semantically relevant based on overall profile similarity"

# -------------------------------------------------
# UI Header
# -------------------------------------------------
st.markdown("<h1 style='text-align:center'>GenAI-Powered Job Search Assistant</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;font-size:1.05rem'>Resume-aware job ranking using embeddings and retrieval</p>",
    unsafe_allow_html=True
)

# -------------------------------------------------
# Sidebar
# -------------------------------------------------
with st.sidebar:
    st.markdown("### 🔍 Search Configuration")

    job_role = st.text_input("Job Title", placeholder="e.g., AI Engineer")
    location = st.text_input("Location", placeholder="e.g., New York")

    resume_file = st.file_uploader(
        "Upload Resume (PDF)",
        type=["pdf"],
        help="Used for semantic job matching"
    )

    st.markdown("---")

    results_wanted = st.slider("Number of Results", 5, 50, 15, step=5)
    experience_level = st.selectbox(
        "Experience Level",
        ["All Levels", "Entry Level", "Mid Level", "Senior Level"]
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
        with st.spinner("Scraping jobs and applying GenAI-based ranking..."):
            try:
                search_term = job_role
                if experience_level != "All Levels":
                    search_term = f"{experience_level.lower()} {job_role}"

                country = (
                    country_override
                    if country_override != "Auto-detect"
                    else determine_country(location)
                )

                jobs_df = scrape_jobs(
                    site_name=["indeed", "linkedin", "zip_recruiter", "glassdoor"],
                    search_term=search_term,
                    location=location,
                    results_wanted=results_wanted,
                    hours_old=72,
                    country_indeed=country
                )

                if jobs_df.empty:
                    st.info("No jobs found.")
                else:
                    if resume_file:
                        resume_text = extract_resume_text(resume_file)

                        if resume_text:
                            jobs_df = rank_jobs_with_rag(resume_text, jobs_df)

                            jobs_df["match_reason"] = jobs_df.apply(
                                lambda r: generate_match_reason(resume_text, r.get("description", "")),
                                axis=1
                            )

                            st.success("Jobs ranked using embedding-based retrieval (RAG).")

                    st.markdown(
                        f"<h3 style='text-align:center'>Top {len(jobs_df)} Jobs</h3>",
                        unsafe_allow_html=True
                    )

                    for _, row in jobs_df.iterrows():
                        st.markdown(
                            f"""
                            <div style="
                                background:white;
                                padding:1.5rem;
                                border-radius:12px;
                                margin-bottom:1rem;
                                box-shadow:0 4px 12px rgba(0,0,0,0.08)
                            ">
                                <a href="{row.get('job_url', '#')}" target="_blank"
                                   style="font-size:1.1rem;font-weight:700">
                                    {row.get('title', 'N/A')}
                                </a>
                                <div>{row.get('company', 'N/A')} — {row.get('location', 'N/A')}</div>
                                <div style="color:green;font-weight:600">
                                    Match Score: {row.get('match_score', 0)}%
                                </div>
                                <div style="font-size:0.9rem;color:#555">
                                    {row.get('match_reason', '')}
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
    "<p style='text-align:center'>Built by Akash Karri | GenAI + Retrieval Systems</p>",
    unsafe_allow_html=True
)
