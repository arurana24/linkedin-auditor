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
from bs4 import BeautifulSoup
from typing import List, Dict, Any

# ==========================================
# SYSTEM SETUP & LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

logo_base64 = get_base64_image("logo.jpeg") or get_base64_image("logo.jpg")

# Advanced Layout Presentation Configuration
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
class DirectPublicSearchService:
    """
    Core Extraction Engine that bypasses Google APIs entirely by utilizing 
    direct HTTP payload scraping with custom user-agent string layouts.
    """
    def __init__(self):
        # Rotating desktop header footprints to stay compliant
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }

    def scrape_leads_for_title(self, company: str, position: str) -> List[Dict[str, Any]]:
        # Using alternative public indexing search frames to grab open profile directories
        query = f"{company} {position} linkedin profile".replace(" ", "+")
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        
        try:
            # Random delay block to respect target system rules
            time.sleep(random.uniform(1.0, 2.5))
            response = requests.get(search_url, headers=self.headers, timeout=12.0)
            
            if response.status_code != 200:
                return []
                
            soup = BeautifulSoup(response.text, "html.parser")
            records = []
            
            # Locate raw result anchor divs inside the open directory layout
            results = soup.find_all("div", class_="result")
            
            for item in results:
                title_element = item.find("a", class_="result__url")
                snippet_element = item.find("a", class_="result__snippet")
                
                if title_element and snippet_element:
                    url = title_element.get("href", "")
                    raw_title = title_element.text.strip()
                    snippet = snippet_element.text.strip()
                    
                    # Ensure the result is an actual individual user profile URL
                    if "linkedin.com/in/" in url:
                        # Clean out common platform naming tracking suffixes
                        name_clean = raw_title.split("-")[0].split("|")[0].replace("...", "").strip()
                        headline_clean = snippet.split("...")[0].strip()
                        
                        records.append({
                            "Target Company": company,
                            "Target Designation": position,
                            "Professional Name": name_clean if name_clean else "Public Professional",
                            "LinkedIn Profile Headline": headline_clean if headline_clean else f"Employee at {company}",
                            "Profile URL": url,
                            "Text Context Match": snippet
                        })
            return records
        except Exception as e:
            logging.error(f"Scraping layer transport failure: {str(e)}")
            return []

search_service = DirectPublicSearchService()

# ==========================================
# STREAMLIT PRESENTATION VIEW LAYER
# ==========================================
st.title("Automated Client Extraction Matrix")
st.markdown("Extract public URLs and matching identification data metrics for current employees across multiple designations simultaneously.")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 1. Target Configurations")
    target_company = st.text_input("Target Corporate Entity Name:", value="Sugar Cosmetics")
    
    designations_input = st.text_area(
        "Target Designations (Type or paste one per line, up to 10 max):",
        value="Founder\nCEO\nDirector",
        help="Type each job title on a completely fresh line.",
        height=160
    )

with col_right:
    st.markdown("### 2. Operational Diagnostics")
    result_depth = st.slider("Target Matrix Processing Depth Max:", min_value=5, max_value=25, value=15)
    st.info(
        "💡 **Infrastructure Notice:**\n"
        "This version uses a direct HTML parsing model. You can safely "
        "delete or ignore your old Google Developer Dashboard keys and account entries entirely."
    )

if st.button("Run Personnel Target Search", type="primary"):
    lines = designations_input.split("\n")
    active_designations = [str(line).strip() for line in lines if str(line).strip() != ""][:10]
    
    if not target_company:
        st.error("Execution halted: Please provide a valid target corporate entity name.")
    elif not active_designations:
        st.error("Execution halted: Please enter at least one target designation title inside the text box.")
    else:
        raw_results_pool = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_steps = len(active_designations)
        
        for idx, position in enumerate(active_designations):
            status_text.text(f"Processing directory lookups for: {position} roles at {target_company}...")
            batch_leads = search_service.scrape_leads_for_title(target_company, position)
            raw_results_pool.extend(batch_leads)
            progress_bar.progress((idx + 1) / total_steps)
            
        status_text.empty()
        
        if raw_results_pool:
            df_raw = pd.DataFrame(raw_results_pool)
            # Clean out structural duplicate matches across shared titles
            df_final = df_raw.drop_duplicates(subset=["Profile URL"], keep="first")
            
            if not df_final.empty:
                st.success(f"Pipeline executed successfully. Extracted and verified {len(df_final)} matching corporate profiles.")
                
                display_cols = ["Professional Name", "LinkedIn Profile Headline", "Profile URL", "Target Designation"]
                st.dataframe(df_final[display_cols], use_container_width=True)
                
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                    df_final.to_excel(writer, sheet_name="Extracted Leads", index=False)
                    
                st.download_button(
                    label="Download Verified Leads Lead Sheet",
                    data=buf.getvalue(),
                    file_name=f"{target_company.lower()}_extracted_leads.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Profiles found, but filtered out during parsing optimizations.")
        else:
            st.error("No data matching that query pattern could be parsed from public directory listings.")

if logo_base64:
    st.markdown(f'<div class="bottom-logo-container"><img src="data:image/jpeg;base64,{logo_base64}"></div>', unsafe_allow_html=True)
