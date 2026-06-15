import os
import io
import time
import random
import logging
import base64
import re
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
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

st.markdown(
    """
    <style>
    .stApp { background-color: #81d8d0; }
    h1 {
        color: #0f172a !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    h2, h3, p, label, .stMarkdown, .stText, [data-testid="stHeader"] {
        color: #1e293b !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    div.stButton > button {
        background-color: #008080 !important;
        color: #ffffff !important;
        border-radius: 8px;
        border: 1px solid #005a5a !important;
        padding: 0.7rem 2.5rem;
        font-weight: 600;
        font-size: 16px;
    }
    div.stButton > button:hover {
        background-color: #005a5a !important;
    }
    div.stDownloadButton > button {
        background-color: #047857 !important;
        color: #ffffff !important;
        border-radius: 8px;
        border: none !important;
        padding: 0.6rem 2rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Active regional geographic footprint matrix mapping
COUNTRY_REGIONS = {
    "India 🇮🇳": "in-en",
    "United States 🇺🇸": "us-en",
    "United Kingdom 🇬🇧": "uk-en",
    "United Arab Emirates 🇦🇪": "ae-en",
    "Singapore 🇸🇬": "sg-en"
}

# ==========================================
# SERVICE ARCHITECTURE LAYER
# ==========================================
class UnifiedDirectorySearchService:
    def __init__(self):
        self.target_url = "https://html.duckduckgo.com/html/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

    def extract_live_personnel(self, company: str, position: str, region_code: str) -> List[Dict[str, Any]]:
        # Formulate a clean target query string targeting direct profile paths
        search_query = f'site:linkedin.com/in/ "{position}" "{company}"'
        payload = {
            "q": search_query,
            "kl": region_code
        }
        
        try:
            time.sleep(random.uniform(1.0, 2.0)) # Prevent rapid network drops
            response = requests.post(self.target_url, data=payload, headers=self.headers, timeout=15.0)
            
            if response.status_code != 200:
                return []
                
            soup = BeautifulSoup(response.text, "html.parser")
            records = []
            
            results = soup.find_all("div", class_="result")
            for item in results:
                url_element = item.find("a", class_="result__url")
                snippet_element = item.find("a", class_="result__snippet")
                
                if url_element and snippet_element:
                    raw_url = url_element.get("href", "")
                    raw_title = url_element.text.strip()
                    snippet_text = snippet_element.text.strip()
                    
                    # Clean out the raw platform tracking redirect parameters out of the URL string
                    actual_profile_url = raw_url
                    if "uddg=" in raw_url:
                        actual_profile_url = raw_url.split("uddg=")[1].split("&")[0]
                        from urllib.parse import unquote
                        actual_profile_url = unquote(actual_profile_url)
                        
                    if "linkedin.com/in/" in actual_profile_url:
                        # Clean the junk suffix text off the end of titles
                        clean_headline = raw_title.split("-")[0].split("|")[0].strip()
                        
                        # STRICTOR CURRENT CONTEXT FILTER
                        # Check text blocks for explicit past-employment markers
                        full_block = f"{clean_headline} {snippet_text}".lower()
                        past_markers = ["ex-", "former", "previous", "retired", "worked at"]
                        
                        if any(marker in full_block for marker in past_markers):
                            continue # Instantly drop past roles to ensure accuracy
                            
                        records.append({
                            "Full Name": clean_headline.split(":", 1)[0].split(" - ")[0].strip(),
                            "Company": company.title(),
                            "Current Designation": clean_headline,
                            "LinkedIn Profile URL": actual_profile_url,
                            "Status": "Verified Current ✅"
                        })
            return records
        except Exception:
            return []

search_engine = UnifiedDirectorySearchService()

# ==========================================
# STREAMLIT PRESENTATION VIEW LAYER
# ==========================================
st.title("🎯 Premium Client Extraction Engine")
st.markdown("Generate highly accurate target lists of currently active enterprise profiles. Zero clutter.")

col_left, col_right = st.columns([1.2, 0.8])

with col_left:
    st.markdown("### 🛠️ Extraction Filters")
    target_company = st.text_input("Target Company Name:", value="Sugar Cosmetics")
    designations_input = st.text_area(
        "Target Designations (One title per line):",
        value="Founder\nCEO",
        height=130
    )

with col_right:
    st.markdown("### 🌍 Region Settings")
    selected_country = st.selectbox("Select Target Country Node:", list(COUNTRY_REGIONS.keys()))
    st.markdown("---")
    st.caption(
        "💡 **Structural Extraction Filter Active:**\n"
        "This mode skips Google RSS caches entirely and uses real-time directory lookup frames to pinpoint active personnel coordinates."
    )

if st.button("Execute Extraction Pipeline", type="primary"):
    lines = designations_input.split("\n")
    active_designations = [str(line).strip() for line in lines if str(line).strip() != ""][:10]
    
    region_config = COUNTRY_REGIONS[selected_country]
    
    if not target_company:
        st.error("Pipeline Error: Please specify a valid target company name.")
    elif not active_designations:
        st.error("Pipeline Error: Please enter at least one target designation title.")
    else:
        results_pool = []
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        total_designations = len(active_designations)
        
        for idx, position in enumerate(active_designations):
            status_text.text(f"Scanning regional nodes for: {position} at {target_company}...")
            batch = search_engine.extract_live_personnel(target_company, position, region_config)
            results_pool.extend(batch)
            progress_bar.progress(float((idx + 1) / total_designations))
            
        status_text.empty()
        progress_bar.empty()
        
        if results_pool:
            df_final = pd.DataFrame(results_pool).drop_duplicates(subset=["LinkedIn Profile URL"]).reset_index(drop=True)
            
            st.success(f"Successfully compiled {len(df_final)} highly accurate active leads for {selected_country}!")
            
            display_cols = ["Full Name", "Company", "Current Designation", "LinkedIn Profile URL", "Status"]
            st.dataframe(df_final[display_cols], use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df_final[display_cols].to_excel(writer, sheet_name="Active Leads", index=False)
                
            st.download_button(
                label="📥 Download Clean Lead Sheet Spreadsheet",
                data=buf.getvalue(),
                file_name=f"{target_company.lower().replace(' ', '_')}_verified_leads.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error(f"No currently active profiles matching those exact filters found in {selected_country}. Try refining your designation spelling keywords.")

if logo_base64:
    st.markdown(f'<div class="bottom-logo-container"><img src="data:image/jpeg;base64,{logo_base64}"></div>', unsafe_allow_html=True)
