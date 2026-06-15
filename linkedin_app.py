import os
import re
import time
import random
import logging
import io
import base64
import pandas as pd
import streamlit as st
import requests
from typing import List, Dict, Any

# ==========================================
# SYSTEM SETUP & LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_SEARCH_API_KEY"]
    GOOGLE_CSE_ID = st.secrets["GOOGLE_CSE_CX_ID"]
except Exception as e:
    st.error("System Configuration Error: Missing 'GOOGLE_SEARCH_API_KEY' or 'GOOGLE_CSE_CX_ID' in Streamlit Secrets.")
    st.stop()

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

logo_base64 = get_base64_image("logo.jpeg") or get_base64_image("logo.jpg")

# Advanced CSS Styling Configuration
st.markdown(
    """
    <style>
    .stApp { background-color: #81d8d0; }
    h1, h2, h3, p, label, .stMarkdown, .stText, [data-testid="stHeader"] {
        color: #1e293b !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    div.stButton > button, div.stDownloadButton > button {
        background-color: #008080 !important;
        color: #ffffff !important;
        border-radius: 6px;
        border: 1px solid #005a5a !important;
        padding: 0.6rem 2.5rem;
        font-weight: bold;
        font-size: 16px;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: #005a5a !important;
        color: #ffffff !important;
    }
    .stProgress > div > div > div > div { background-color: #008080 !important; }
    .bottom-logo-container {
        display: flex; justify-content: center; align-items: center; width: 100%;
        margin-top: 50px; padding-top: 20px; margin-bottom: 20px;
    }
    .bottom-logo-container img { width: 140px; border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# SERVICE ARCHITECTURE LAYER
# ==========================================
class LinkedInSearchService:
    """
    Core Search Service Engine utilizing Google Custom Search API 
    for decoupled, account-safe LinkedIn X-Ray queries.
    """
    def __init__(self, api_key: str, cse_id: str):
        self._api_key = api_key
        self._cse_id = cse_id
        self._base_url = "https://www.googleapis.com/customsearch/v1"

    @staticmethod
    def clean_profile_title(raw_title: str) -> tuple:
        """
        Parses professional names and title headlines from raw Google metadata string boundaries.
        """
        if not raw_title:
            return "Unknown", "Unknown"
        clean_string = re.sub(r'\s*[\s|│-]\s*LinkedIn\s*$', '', raw_title, flags=re.IGNORECASE)
        parts = re.split(r'\s*[\s|│-]\s*', clean_string)
        name = parts[0].strip() if len(parts) > 0 else "Unknown Name"
        headline = parts[1].strip() if len(parts) > 1 else "Professional Profile"
        return name, headline

    @staticmethod
    def calculate_confidence_score(snippet: str, headline: str, company: str, position: str) -> float:
        """
        Calculates a lead verification confidence score from 0.0 to 1.0 based on keywords.
        """
        score = 0.0
        snippet_lower = snippet.lower()
        headline_lower = headline.lower()
        company_lower = company.lower()
        pos_lower = position.lower()

        if company_lower in headline_lower:
            score += 0.45
        elif f"at {company_lower}" in snippet_lower or "current:" in snippet_lower:
            score += 0.35

        if pos_lower in headline_lower or any(t in headline_lower for t in pos_lower.split()):
            score += 0.35

        # Penalize data if past-employment keywords are found
        exclusion_tokens = ["former", "past:", "ex-", "previously", "retired", "student at"]
        for token in exclusion_tokens:
            if token in snippet_lower or token in headline_lower:
                score -= 0.50

        return max(0.0, min(float(score), 1.0))

    def fetch_leads_for_designation(self, company: str, position: str, max_depth: int = 10) -> List[Dict[str, Any]]:
        """
        Queries Google's API index using rigorous boolean constraints to filter for active targets.
        """
        search_query = f'site:linkedin.com/in/ "{company}" "{position}" "current" -intitle:past'
        params = {
            "key": self._api_key,
            "cx": self._cse_id,
            "q": search_query,
            "num": min(max(max_depth, 1), 10)
        }

        try:
            time.sleep(random.uniform(0.2, 0.4))  # Human pacing element
            response = requests.get(self._base_url, params=params, timeout=10.0)
            
            if response.status_code == 429:
                st.error("🚨 HTTP 429 Error: Your hourly or daily Google Search Quota is completely exhausted.")
                return []
            response.raise_for_status()
            
            items = response.json().get("items", [])
            records = []

            for item in items:
                raw_title = item.get("title", "")
                snippet = item.get("snippet", "")
                profile_url = item.get("link", "")

                if "former" in snippet.lower() or "past:" in snippet.lower():
                    if f"at {company.lower()}" not in snippet.lower() and "current:" not in snippet.lower():
                        continue

                name, headline = self.clean_profile_title(raw_title)
                confidence = self.calculate_confidence_score(snippet, headline, company, position)

                records.append({
                    "Target Company": company,
                    "Target Designation": position,
                    "Professional Name": name,
                    "LinkedIn Profile Headline": headline,
                    "Profile URL": profile_url,
                    "Verification Snippet": snippet,
                    "Lead Confidence Score": confidence
                })
            return records
        except Exception as e:
            logging.error(f"Network backend layer execution error: {str(e)}")
            return []

# Initialize search engine core interface
search_service = LinkedInSearchService(api_key=GOOGLE_API_KEY, cse_id=GOOGLE_CSE_ID)

# ==========================================
# STREAMLIT PRESENTATION VIEW LAYER
# ==========================================
st.title("LinkedIn Personnel Identification Matrix")
st.markdown("Extract public URLs and matching verification metrics for **current** corporate employees across multiple designations simultaneously.")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 1. Target Configurations")
    target_company = st.text_input("Target Corporate Entity Name:", value="Google")
    
    # REPLACED st.data_editor WITH A BULLETPROOF TEXT AREA FIELD
    designations_input = st.text_area(
        "Target Designations (Type or paste one per line, up to 10 max):",
        value="Product Manager\nSoftware Engineer",
        help="Type each job title on a completely fresh line.",
        height=160
    )

with col_right:
    st.markdown("### 2. Execution Toggles")
    result_depth = st.slider("Max Result Rows per Designation:", min_value=5, max_value=10, value=10)
    min_confidence = st.slider("Minimum Acceptable Lead Confidence Gate:", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
    st.info(
        "💡 **Data Engineering Architecture Notice:**\n"
        "This system filters out past employees using a dynamic confidence scoring model and regex filters, "
        "completely bypassing standard LinkedIn scraping limits."
    )

if st.button("Run Personnel Target Search", type="primary"):
    # Convert text area lines into a clean Python list of titles
    lines = designations_input.split("\n")
    active_designations = [str(line).strip() for line in lines if str(line).strip() != ""][:10] # Enforce max 10 titles cap
    
    if not target_company:
        st.error("Execution halted: Please provide a valid target corporate entity name.")
    elif not active_designations:
        st.error("Execution halted: Please enter at least one target designation title inside the text box.")
    else:
        raw_results_pool = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_steps = len(active_designations)
        
        # Sequentially scan target fields
        for idx, position in enumerate(active_designations):
            status_text.text(f"Querying indexing servers for: {position} roles at {target_company}...")
            batch_leads = search_service.fetch_leads_for_designation(target_company, position, result_depth)
            raw_results_pool.extend(batch_leads)
            progress_bar.progress((idx + 1) / total_steps)
            
        status_text.empty()
        
        if raw_results_pool:
            # --- ADVANCED POST-PROCESSING STAGES ---
            df_raw = pd.DataFrame(raw_results_pool)
            
            # 1. Enforce strict profile URL deduplication (keeps the entry with the highest confidence score)
            df_raw = df_raw.sort_values(by="Lead Confidence Score", ascending=False)
            df_clean = df_raw.drop_duplicates(subset=["Profile URL"], keep="first")
            
            # 2. Filter out records that fall below our minimum confidence score threshold
            df_final = df_clean[df_clean["Lead Confidence Score"] >= min_confidence]
            
            if not df_final.empty:
                st.success(f"Pipeline executed successfully. Extracted and verified {len(df_final)} unique corporate profiles.")
                
                # Format view output column order cleanly
                display_cols = ["Professional Name", "LinkedIn Profile Headline", "Profile URL", "Lead Confidence Score", "Target Designation"]
                st.dataframe(df_final[display_cols].sort_values(by="Lead Confidence Score", ascending=False), use_container_width=True)
                
                # Compile multi-sheet clean excel data workspace memory streams
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                    df_final.to_excel(writer, sheet_name="Active Verified Leads", index=False)
                    df_clean.to_excel(writer, sheet_name="All Extracted Records", index=False)
                    
                st.download_button(
                    label="Download Verified Leads Lead Sheet",
                    data=buf.getvalue(),
                    file_name=f"{target_company.lower()}_verified_leads_matrix.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("All extracted leads were dropped because they fell below your Minimum Confidence Gate. Try lowering the slider filter.")
        else:
            st.error("No data could be indexed from the public search vectors. Check your corporate search term spelling or API key limits.")

if logo_base64:
    st.markdown(f'<div class="bottom-logo-container"><img src="data:image/jpeg;base64,{logo_base64}"></div>', unsafe_allow_html=True)
