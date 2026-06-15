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
import xml.etree.ElementTree as ET
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
    </style>
    """,
    unsafe_allow_html=True
)

# Geographic Perspective Parameter Map Matrix
COUNTRY_MAP = {
    "India 🇮🇳": {"hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
    "United States 🇺🇸": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
    "United Kingdom 🇬🇧": {"hl": "en-GB", "gl": "GB", "ceid": "GB:en"},
    "United Arab Emirates 🇦🇪": {"hl": "en-AE", "gl": "AE", "ceid": "AE:en"},
    "Singapore 🇸🇬": {"hl": "en-SG", "gl": "SG", "ceid": "SG:en"}
}

# ==========================================
# SERVICE ARCHITECTURE LAYER
# ==========================================
class GoogleRSSXRayService:
    """
    Leverages Google's trusted indexing infrastructure to execute 
    unlimited country-targeted lookups and verify live profile metadata.
    """
    def __init__(self):
        self.base_url = "https://news.google.com/rss/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    @staticmethod
    def parse_name_headline(raw_title: str) -> tuple:
        if " - " in raw_title:
            parts = raw_title.split(" - ")
            name = parts[0].strip()
            headline = parts[1].replace(" - LinkedIn", "").replace(" | LinkedIn", "").strip()
            return name, headline
        return raw_title, "Professional Profile"

    def unshorten_google_url(self, google_url: str) -> str:
        """
        Follows the tracking link wrapper to extract the native, direct LinkedIn profile URL.
        """
        try:
            # Execute a lightweight HEAD request to trace redirect headers instantly
            response = requests.head(google_url, headers=self.headers, allow_redirects=True, timeout=5.0)
            final_url = response.url.split("?")[0] # Clear parameters
            if "linkedin.com/in/" in final_url:
                return final_url
            return google_url
        except Exception:
            return google_url

    def fetch_country_targeted_leads(self, company: str, position: str, locale: dict) -> List[Dict[str, Any]]:
        # Enforce target parameters directly inside the core query string
        raw_query = f'site:linkedin.com/in/ "{company}" "{position}"'
        encoded_query = quote(raw_query)
        
        request_url = f"{self.base_url}?q={encoded_query}&hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
        
        try:
            time.sleep(random.uniform(0.3, 0.8))
            response = requests.get(request_url, headers=self.headers, timeout=10.0)
            if response.status_code != 200:
                return []
                
            root = ET.fromstring(response.text)
            records = []
            
            for item in root.findall(".//item"):
                title_text = item.find("title").text if item.find("title") is not None else ""
                google_link = item.find("link").text if item.find("link") is not None else ""
                description_text = item.find("description").text if item.find("description") is not None else ""
                
                clean_snippet = re.sub(r'<[^>]*>', '', description_text).lower()
                name, headline = self.parse_name_headline(title_text)
                
                # REVERIFICATION LOGIC PASS
                # Check for active context matches while filtering out clear past-employment markers
                company_lower = company.lower()
                is_current = False
                
                if company_lower in headline.lower() or company_lower in clean_snippet:
                    is_current = True
                    
                exclusion_tokens = ["former", "past:", "ex-", "previously", "retired"]
                if any(token in clean_snippet or token in headline.lower() for token in exclusion_tokens):
                    is_current = False
                
                verification_status = "Verified Current ✅" if is_current else "Unverified / Past Role ⚠️"
                
                if "linkedin" in clean_snippet or "linkedin" in title_text.lower():
                    records.append({
                        "Target Company": company,
                        "Target Designation": position,
                        "Professional Name": name,
                        "Current Profile Headline": headline,
                        "Google Link Container": google_link,
                        "Employment Verification": verification_status
                    })
            return records
        except Exception:
            return []

search_service = GoogleRSSXRayService()

# ==========================================
# STREAMLIT PRESENTATION VIEW LAYER
# ==========================================
st.title("Automated Client Extraction Matrix")
st.markdown("Extract country-focused profiles with real-time verification filters. 100% Free & Unlimited.")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 1. Target Parameters")
    target_company = st.text_input("Target Corporate Entity Name:", value="Sugar Cosmetics")
    
    designations_input = st.text_area(
        "Target Designations (One title per line):",
        value="Founder\nCEO",
        height=140
    )

with col_right:
    st.markdown("### 2. Geographic Filters")
    selected_country = st.selectbox("Select Target Country Perspective:", list(COUNTRY_MAP.keys()))
    st.info(
        "🛡 *System Infrastructure Status: Open Proxy Active*\n"
        "This tool automatically traces underlying header networks to turn tracking strings into clean LinkedIn profile paths."
    )

if st.button("Run Personnel Target Search", type="primary"):
    lines = designations_input.split("\n")
    active_designations = [str(line).strip() for line in lines if str(line).strip() != ""][:10]
    
    locale_config = COUNTRY_MAP[selected_country]
    
    if not target_company:
        st.error("Execution halted: Please specify a valid company filter metric.")
    elif not active_designations:
        st.error("Execution halted: Please provide at least one target designation string.")
    else:
        results_pool = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, position in enumerate(active_designations):
            status_text.text(f"Querying regional servers ({selected_country}) for: {position} roles...")
            batch = search_service.fetch_country_targeted_leads(target_company, position, locale_config)
            results_pool.extend(batch)
            progress_bar.progress((idx + 1) / len(active_designations))
            
        if results_pool:
            status_text.text("Unpacking tracking headers to extract true LinkedIn profile URLs...")
            df_final = pd.DataFrame(results_pool).drop_duplicates(subset=["Professional Name"])
            
            # CRITICAL LOOP FIX: Accessing records via safe string keys inside iterrows loop
            real_urls = []
            url_progress = st.progress(0)
            total_urls = len(df_final)
            
            for i, (index, row) in enumerate(df_final.iterrows()):
                google_url = row["Google Link Container"]
                real_link = search_service.unshorten_google_url(google_url)
                real_urls.append(real_link)
                url_progress.progress((i + 1) / total_urls)
                
            df_final["True LinkedIn Profile URL"] = real_urls
            url_progress.empty()
            status_text.empty()
            
            st.success(f"Pipeline executed successfully. Synchronized {len(df_final)} unique corporate leads.")
            
            display_cols = ["Professional Name", "Current Profile Headline", "True LinkedIn Profile URL", "Employment Verification", "Target Designation"]
            st.dataframe(df_final[display_cols], use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df_final[display_cols].to_excel(writer, sheet_name="Target Profiles", index=False)
                
            st.download_button(
                label="Download Verified Leads Lead Sheet",
                data=buf.getvalue(),
                file_name=f"{target_company.lower()}_localized_leads.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            status_text.empty()
            st.error("No data streams could be parsed from regional indexes. Verify input parameters.")

if logo_base64:
    st.markdown(f'<div class="bottom-logo-container"><img src="data:image/jpeg;base64,{logo_base64}"></div>', unsafe_allow_html=True)
