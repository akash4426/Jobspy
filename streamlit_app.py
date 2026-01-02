import streamlit as st
import pandas as pd
from jobspy import scrape_jobs
from datetime import datetime
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Job Spy - ML Powered Job Search",
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

# -------------------------------------------------
# Helper Functions
# -------------------------------------------------
def extract_resume_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def determine_country(location_text):
    loc = location_text.lower()
    if "india" in loc:
        return "India"
    if "canada" in loc:
        return "Canada"
    if "uk" in loc or "united kingdom" in loc:
        return "UK"
    if "australia" in loc:
        return "Australia"
    if "germany" in loc:
        return "Germany"
    if "france" in loc:
        return "France"
    if "singapore" in loc:
        return "Singapore"
    return "USA"

def compute_match_scores(resume_text, jobs_df):
    job_texts = jobs_df["description"].fillna("").tolist()

    resume_embedding = model.encode([resume_text])
    job_embeddings = model.encode(job_texts)

    scores = cosine_similarity(resume_embedding, job_embeddings)[0]
    jobs_df["match_score"] = (scores * 100).round(2)

    return jobs_df

# -------------------------------------------------
# UI Header
# -------------------------------------------------
st.markdown("<h1 style='text-align:center'>ML-Powered Job Search Portal</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;font-size:1.1rem'>Resume-aware job ranking using NLP</p>",
    unsafe_allow_html=True
)

# -------------------------------------------------
# Sidebar
# -------------------------------------------------
with st.sidebar:
    st.markdown("### 🔍 Search Configuration")

    job_role = st.text_input("Job Title", placeholder="e.g., Software Engineer")
    location = st.text_input("Location", placeholder="e.g., New York")

    resume_file = st.file_uploader(
        "Upload Resume (PDF)",
        type=["pdf"],
        help="Used for ML-based job matching"
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
        with st.spinner("Searching jobs and applying ML ranking..."):
            try:
                search_term = job_role
                if experience_level != "All Levels":
                    search_term = f"{experience_level.lower()} {job_role}"

                country = (
                    country_override
                    if country_override != "Auto-detect"
                    else determine_country(location)
                )

                params = {
                    "site_name": ["indeed", "linkedin", "zip_recruiter", "glassdoor"],
                    "search_term": search_term,
                    "location": location,
                    "results_wanted": results_wanted,
                    "hours_old": 72,
                    "country_indeed": country
                }

                jobs_df = scrape_jobs(**params)

                if jobs_df.empty:
                    st.info("No jobs found.")
                else:
                    # ML-based ranking
                    if resume_file:
                        resume_text = extract_resume_text(resume_file)
                        if resume_text.strip():
                            jobs_df = compute_match_scores(resume_text, jobs_df)
                            jobs_df = jobs_df.sort_values("match_score", ascending=False)
                            st.success("Jobs ranked using ML-based resume matching.")
                    else:
                        if "date_posted" in jobs_df.columns:
                            jobs_df["date_posted"] = pd.to_datetime(
                                jobs_df["date_posted"], errors="coerce"
                            )
                            jobs_df = jobs_df.sort_values("date_posted", ascending=False)

                    # -------------------------------------------------
                    # Results
                    # -------------------------------------------------
                    st.markdown(
                        f"<h3 style='text-align:center'>Found {len(jobs_df)} Jobs</h3>",
                        unsafe_allow_html=True
                    )

                    tab1, tab2 = st.tabs(["Card View", "Table View"])

                    # ---------------- Card View ----------------
                    with tab1:
                        for _, row in jobs_df.iterrows():
                            title = row.get("title", "N/A")
                            company = row.get("company", "N/A")
                            loc = row.get("location", "N/A")
                            url = row.get("job_url", "#")
                            score = row.get("match_score")

                            score_html = (
                                f"<span style='color:green;font-weight:600'>Match: {score}%</span>"
                                if pd.notna(score)
                                else ""
                            )

                            st.markdown(
                                f"""
                                <div style="
                                    background:white;
                                    padding:1.5rem;
                                    border-radius:12px;
                                    margin-bottom:1rem;
                                    box-shadow:0 4px 12px rgba(0,0,0,0.1)
                                ">
                                    <a href="{url}" target="_blank"
                                       style="font-size:1.2rem;font-weight:700">
                                        {title}
                                    </a>
                                    <div>{company}</div>
                                    <div>{loc}</div>
                                    <div>{score_html}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                    # ---------------- Table View ----------------
                    with tab2:
                        display_cols = [
                            "title", "company", "location",
                            "match_score", "site", "job_url"
                        ]
                        available = [c for c in display_cols if c in jobs_df.columns]

                        st.dataframe(
                            jobs_df[available],
                            use_container_width=True,
                            column_config={
                                "job_url": st.column_config.LinkColumn("View Job"),
                                "match_score": st.column_config.NumberColumn("Match %", format="%.2f")
                            }
                        )

                    # ---------------- Download ----------------
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
    "<p style='text-align:center'>Made with ❤️ by Akash Karri</p>",
    unsafe_allow_html=True
)
