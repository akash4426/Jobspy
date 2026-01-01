import streamlit as st
import pandas as pd
from jobspy import scrape_jobs
from datetime import datetime
import os

# Page Configuration
st.set_page_config(
    page_title="Job Spy - Your Job Search Assistant",
    page_icon="favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern Interactive UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styling */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: #000000;
    }
    
    /* Main Background with Gradient */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    
    /* Header Styling */
    h1 {
        font-weight: 700;
        font-size: 3rem;
        color: #000000;
        margin-bottom: 0.5rem;
        text-align: center;
        letter-spacing: -1px;
    }
    
    h2 {
        color: #1a1a1a;
        font-weight: 600;
        font-size: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    h3 {
        color: #1a1a1a;
        font-weight: 600;
        font-size: 1.2rem;
    }
    
    /* Subtitle */
    .subtitle {
        text-align: center;
        color: #2d3748;
        font-size: 1.2rem;
        font-weight: 400;
        margin-bottom: 2rem;
        letter-spacing: 0.5px;
    }
    
    /* Sidebar Styling - Dark Theme */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(26, 32, 44, 0.95) 0%, rgba(45, 55, 72, 0.95) 100%);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    section[data-testid="stSidebar"] > div {
        padding-top: 2rem;
    }
    
    /* Sidebar Text Colors */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Sidebar Input Fields */
    section[data-testid="stSidebar"] .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.1);
        border: 2px solid rgba(255, 255, 255, 0.2);
        color: white;
    }
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input::placeholder {
        color: rgba(255, 255, 255, 0.5);
    }
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input:focus {
        background: rgba(255, 255, 255, 0.15);
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
    }
    
    /* Sidebar Select Boxes */
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.1);
        border: 2px solid rgba(255, 255, 255, 0.2);
    }
    
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.1);
        color: white;
    }
    
    /* Sidebar Slider */
    section[data-testid="stSidebar"] .stSlider > div > div > div > div {
        color: white;
    }
    
    /* Sidebar Expander */
    section[data-testid="stSidebar"] .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.1);
        color: white !important;
    }
    
    section[data-testid="stSidebar"] .streamlit-expanderHeader:hover {
        background: rgba(102, 126, 234, 0.3);
    }
    
    /* Sidebar Divider */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.2);
    }
    
    /* Input Fields */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e2e8f0;
        padding: 0.75rem;
        font-size: 1rem;
        transition: all 0.3s ease;
        background: white;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Select Box */
    .stSelectbox > div > div {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    /* Slider */
    .stSlider > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: black;
        border-radius: 12px;
        border: none;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1.1rem;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(72, 187, 120, 0.3);
        transition: all 0.3s ease;
    }
    
    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(72, 187, 120, 0.5);
    }
    
    /* Job Cards */
    .job-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        margin-bottom: 1.25rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .job-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        transform: scaleX(0);
        transition: transform 0.4s ease;
    }
    
    .job-card:hover::before {
        transform: scaleX(1);
    }
    
    .job-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 48px rgba(102, 126, 234, 0.2);
        border-color: rgba(102, 126, 234, 0.3);
    }
    
    .job-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #667eea;
        margin-bottom: 0.75rem;
        text-decoration: none;
        display: inline-block;
        transition: all 0.3s ease;
        line-height: 1.4;
    }
    
    .job-title:hover {
        color: #764ba2;
        transform: translateX(4px);
    }
    
    .job-company {
        font-weight: 600;
        font-size: 1.1rem;
        color: #2d3748;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .job-company::before {
        content: '■';
        color: #667eea;
        font-size: 0.8rem;
    }
    
    .job-location {
        color: #4a5568;
        font-size: 1rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .job-location::before {
        content: '📍';
        font-size: 1rem;
    }
    
    .job-salary {
        display: inline-block;
        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 8px rgba(72, 187, 120, 0.3);
    }
    
    .job-meta {
        display: flex;
        gap: 1.5rem;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(0, 0, 0, 0.1);
        font-size: 0.9rem;
        color: #718096;
        flex-wrap: wrap;
    }
    
    .job-meta-item {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-weight: 500;
    }
    
    .job-meta-item::before {
        content: '●';
        color: #667eea;
        font-size: 0.6rem;
    }
    
    /* Success/Info Messages */
    .stAlert {
        border-radius: 12px;
        border: none;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background: rgba(255, 255, 255, 0.95);
        padding: 1rem;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 1.1rem;
        color: #4a5568;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(102, 126, 234, 0.1);
        color: #667eea;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Dataframe */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.5);
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(102, 126, 234, 0.1);
        color: #667eea;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }
    
    /* Search Container */
    .search-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
    }
    
    /* Results Counter */
    .results-counter {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 2rem;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none;}
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .job-card {
        animation: fadeIn 0.6s ease-out forwards;
    }
    
    .job-card:nth-child(1) { animation-delay: 0.1s; }
    .job-card:nth-child(2) { animation-delay: 0.2s; }
    .job-card:nth-child(3) { animation-delay: 0.3s; }
    .job-card:nth-child(4) { animation-delay: 0.4s; }
    .job-card:nth-child(5) { animation-delay: 0.5s; }
</style>
""", unsafe_allow_html=True)

def determine_country(location_text):
    """Determine country from location text, defaulting to USA"""
    loc_lower = location_text.lower()
    if 'india' in loc_lower:
        return 'India'
    elif 'canada' in loc_lower:
        return 'Canada'
    elif 'uk' in loc_lower or 'united kingdom' in loc_lower or 'britain' in loc_lower:
        return 'UK'
    elif 'australia' in loc_lower:
        return 'Australia'
    elif 'germany' in loc_lower:
        return 'Germany'
    elif 'france' in loc_lower:
        return 'France'
    elif 'singapore' in loc_lower:
        return 'Singapore'
    return 'USA'

def main():
    # Header Section
    st.markdown("<h1>Job Search Portal</h1>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Discover your next career opportunity across multiple platforms</p>', unsafe_allow_html=True)

    # Search Configuration in Sidebar
    with st.sidebar:
        st.markdown("### Search Configuration")
        
        job_role = st.text_input("Job Title", placeholder="e.g., Software Engineer, Data Analyst")
        location = st.text_input("Location", placeholder="e.g., New York, San Francisco")
        
        st.markdown("---")
        
        # Advanced Options
        with st.expander("Advanced Filters", expanded=True):
            results_wanted = st.slider("Number of Results", min_value=5, max_value=50, value=15, step=5)
            
            job_type = st.selectbox(
                "Employment Type",
                ["All Types", "Full-time", "Internship"],
                index=0
            )
            
            experience_level = st.selectbox(
                "Experience Level",
                ["All Levels", "Entry Level", "Mid Level", "Senior Level"],
                index=0
            )
            
            country_override = st.selectbox(
                "Country/Region", 
                ["Auto-detect", "USA", "India", "Canada", "UK", "Australia", "Germany", "France", "Singapore"]
            )
        
        st.markdown("---")
        search_clicked = st.button("Search Jobs", use_container_width=True)
    
    # Main Content Area
    if search_clicked:
        if not job_role or not location:
            st.warning("Please enter both Job Title and Location to begin your search.")
        else:
            # Loading State
            with st.spinner("Searching across multiple job platforms..."):
                try:
                    # Map job type
                    job_type_map = {
                        "Full-time": "fulltime",
                        "Part-time": "parttime",
                        "Internship": "internship",
                        "Contract": "contract"
                    }
                    
                    # Add experience level to search term if specified
                    search_term = job_role
                    if experience_level != "All Levels":
                        exp_keywords = {
                            "Entry Level": "entry level",
                            "Mid Level": "mid level",
                            "Senior Level": "senior"
                        }
                        keyword = exp_keywords.get(experience_level, "")
                        if keyword:
                            search_term = f"{keyword} {job_role}"
                    
                    # Determine country
                    if country_override != "Auto-detect":
                        country_indeed = country_override
                    else:
                        country_indeed = determine_country(location)

                    # Prepare parameters
                    scrape_params = {
                        "site_name": ["indeed", "linkedin", "zip_recruiter", "glassdoor"],
                        "search_term": search_term,
                        "location": location,
                        "results_wanted": results_wanted,
                        "hours_old": 72,
                        "country_indeed": country_indeed
                    }
                    
                    if job_type != "All Types":
                        scrape_params["job_type"] = job_type_map.get(job_type, "")
                    
                    # Scrape jobs
                    jobs_df = scrape_jobs(**scrape_params)
                    
                    if jobs_df.empty:
                        st.info("No positions found matching your criteria. Try adjusting your search parameters.")
                    else:
                        # Process results
                        if 'date_posted' in jobs_df.columns:
                            jobs_df['date_posted'] = pd.to_datetime(jobs_df['date_posted'], errors='coerce')
                            jobs_df = jobs_df.sort_values('date_posted', ascending=False, na_position='last')
                        
                        # Results counter
                        st.markdown(f'<div class="results-counter">Found {len(jobs_df)} Opportunities</div>', unsafe_allow_html=True)
                        
                        # Create tabs for different views
                        tab_cards, tab_table = st.tabs(["Card View", "Table View"])
                        
                        with tab_cards:
                            # Display job cards
                            for index, row in jobs_df.iterrows():
                                title = row.get('title', 'Position Title Not Available')
                                company = row.get('company', 'Company Not Specified')
                                loc = row.get('location', 'Location Not Specified')
                                url = row.get('job_url', '#')
                                salary = row.get('min_amount')
                                date_str = row.get('date_posted', '')
                                site = row.get('site', 'Unknown')
                                
                                # Format date
                                if pd.notna(date_str) and isinstance(date_str, datetime):
                                    date_display = date_str.strftime('%b %d, %Y')
                                else:
                                    date_display = 'Recently'
                                
                                # Build salary display
                                salary_html = ""
                                if salary and pd.notna(salary):
                                    salary_html = f'<div class="job-salary">${salary:,.0f}+</div>'
                                
                                # Render card using Streamlit components
                                with st.container():
                                    st.markdown(f"""
                                    <div class="job-card">
                                        <a href="{url}" target="_blank" class="job-title">{title}</a>
                                        <div class="job-company">{company}</div>
                                        <div class="job-location">{loc}</div>
                                        {salary_html}
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Metadata in columns
                                    meta_col1, meta_col2 = st.columns(2)
                                    with meta_col1:
                                        st.caption(f"📌 {site.title()}")
                                    with meta_col2:
                                        st.caption(f"🕒 {date_display}")
                                    
                                    st.markdown("---")
                        
                        with tab_table:
                            # Display as interactive dataframe
                            display_cols = ['title', 'company', 'location', 'min_amount', 'date_posted', 'site', 'job_url']
                            available_cols = [col for col in display_cols if col in jobs_df.columns]
                            st.dataframe(
                                jobs_df[available_cols],
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "job_url": st.column_config.LinkColumn("View Job"),
                                    "min_amount": st.column_config.NumberColumn("Salary", format="$%.0f"),
                                    "title": "Job Title",
                                    "company": "Company",
                                    "location": "Location",
                                    "date_posted": st.column_config.DateColumn("Posted Date"),
                                    "site": "Source"
                                }
                            )
                        
                        # Download section
                        st.markdown("---")
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            csv = jobs_df.to_csv(index=False).encode('utf-8')
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            st.download_button(
                                label="Download Results as CSV",
                                data=csv,
                                file_name=f"job_search_{job_role.replace(' ', '_')}_{timestamp}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )

                except Exception as e:
                    st.error(f"An error occurred while searching: {str(e)}")
                    st.info("Please try again with different search parameters.")
    else:
        # Welcome message when no search has been performed
        st.markdown("""
        <div class="search-container">
            <h2 style="text-align: center; color: #2d3748; margin-bottom: 1rem;">Get Started</h2>
            <p style="text-align: center; color: #4a5568; font-size: 1.1rem;">
                Enter your desired job title and location in the sidebar to begin your search.<br>
                We'll scan multiple job platforms to find the best opportunities for you.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem 0;">
        <p style="color: #1a1a1a; font-size: 1rem; font-weight: 500;">
            Made with ♥ by Akash Karri
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
