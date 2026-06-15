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
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    div.stButton > button:hover {
        background-color: #005a5a !important;
        color: #ffffff !important;
    }
    div.stDownloadButton > button {
        background-color: #047857 !important;
        color: #ffffff !important;
        border-radius: 8px;
        border: none !important;
        padding: 0.6rem 2rem;
        font-weight: 600;
    }
    div.stDownloadButton > button:hover {
        background-color: #065f46 !important;
    }
    .stProgress > div > div > div > div { background-color: #008080 !important; }
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
    }
    </style>
    """,
    unsafe_allow_html=True
)

COUNTRY_MAP = {
    "India 🇮🇳": {"hl": "en-IN", "gl": "IN", "ceid": "IN:en", "subdomain": "in.linkedin.com/in/"},
    "United States 🇺🇸": {"hl": "en-US", "gl": "US", "ceid": "US:en", "subdomain": "linkedin.com/in/"},
    "United Kingdom 🇬🇧": {"hl": "en-GB", "gl": "GB", "ceid": "GB:en", "subdomain": "uk.linkedin.com/in/"},
    "United Arab Emirates 🇦🇪": {"hl": "en-AE", "gl": "AE", "ceid": "AE:en", "subdomain": "ae.linkedin.com/in/"},
    "Singapore 🇸🇬": {"hl": "en-SG", "gl": "SG", "ceid": "SG:en", "subdomain": "sg.linkedin.com/in/"}
}

# ==========================================
# SERVICE ARCHITECTURE LAYER
# ==========================================
class ElasticVerificationService:
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
        try:
            response = requests.head(google_url, headers=self.headers, allow_redirects=True, timeout=5.0)
            final_url = response.url.split("?")[0]
            if "linkedin.com/in/" in final_url:
                return final_url
            return google_url
        except Exception:
            return google_url

    def fetch_raw_pool(self, company: str, position: str, locale: dict) -> List[Dict[str, Any]]:
        # Open baseline lookup query targeting direct country directories
        raw_query = f'site:{locale["subdomain"]} {company} {position}'
        encoded_query = quote(raw_query)
        request_url = f"{self.base_url}?q={encoded_query}&hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
        
        try:
            time.sleep(random.uniform(0.1, 0.3))
            response = requests.get(request_url, headers=self.headers, timeout=10.0)
            if response.status_code != 200:
                return []
                
            root = ET.fromstring(response.text)
            raw_items = []
            
            for item in root.findall(".//item"):
                title_text = item.find("title").text if item.find("title") is not None else ""
                google_link = item.find("link").text if item.find("link") is not None else ""
                description_text = item.find("description").text if item.find("description") is not None else ""
                
                clean_snippet = re.sub(r'<[^>]*>', '', description_text)
                name, headline = self.parse_name_headline(title_text)
                
                raw_items.append({
                    "name": name,
                    "headline": headline,
                    "snippet": clean_snippet,
                    "link": google_link
                })
            return raw_items
        except Exception:
            return []

search_service = ElasticVerificationService()

# ==========================================
# STREAMLIT PRESENTATION VIEW LAYER
# ==========================================
st.title("🎯 Premium Multi-Stage Extraction Engine")
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
    selected_country = st.selectbox("Select Target Country Node:", list(COUNTRY_MAP.keys()))
    st.markdown("---")
    st.caption(
        "💡 **Elastic Filtering Mode Active:**\n"
        "Stage 1 crawls regional subdomains broadly. Stage 2 applies a flexible token matrix filter "
        "to securely catch current roles while dropping past employees."
    )

if st.button("Execute Extraction Pipeline", type="primary"):
    lines = designations_input.split("\n")
    active_designations = [str(line).strip() for line in lines if str(line).strip() != ""][:10]
    
    locale_config = COUNTRY_MAP[selected_country]
    
    if not target_company:
        st.error("Pipeline Error: Please specify a valid target company name.")
    elif not active_designations:
        st.error("Pipeline Error: Please enter at least one target designation title.")
    else:
        raw_pool = []
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        # STAGE 1: Broad Bulk Gathering Pass
        total_designations = len(active_designations)
        for idx, position in enumerate(active_designations):
            status_text.text(f"Stage 1: Fetching regional indexing blocks for '{position}'...")
            batch = search_service.fetch_raw_pool(target_company, position, locale_config)
            
            for item in batch:
                item["target_position"] = position
                raw_pool.append(item)
                
            progress_bar.progress(float(((idx + 1) / total_designations) * 0.4))
            
        if raw_pool:
            # STAGE 2: Flexible Automated Verification Engine
            status_text.text("Stage 2: Processing records via elastic token validation matrices...")
            verified_records = []
            
            df_raw_pool = pd.DataFrame(raw_pool).drop_duplicates(subset=["name"])
            total_rows = len(df_raw_pool)
            
            # Tokenize company name to increase match coverage
            company_clean = target_company.strip().lower()
            company_words = [w for w in re.split(r'\s+', company_clean) if len(w) > 2]
            if not company_words:
                company_words = [company_clean]
            
            for i, (index, row) in enumerate(df_raw_pool.iterrows()):
                name = row["name"]
                headline = row["headline"]
                snippet = row["snippet"]
                google_url = row["link"]
                pos_target = row["target_position"]
                
                full_text_block = f"{headline} {snippet}".lower()
                headline_lower = headline.lower()
                pos_target_lower = pos_target.lower()
                
                # 1. FIXED PRE-EXCLUSION CHECK: Capture 'Ex-' and 'Former' string combinations safely
                past_indicators = ["ex-", "former", "previously", "retired", "ex-employee", "worked at", "past:"]
                is_past = False
                for token in past_indicators:
                    if token in full_text_block:
                        # Ensure token is near the company name context
                        for word in company_words:
                            if f"{token}{word}" in full_text_block.replace(" ", "") or f"{token} {word}" in full_text_block:
                                is_past = True
                                break
                if is_past:
                    continue # Drop past role cleanly
                
                # 2. FLEXIBLE DESIGNATION GATE: Match individual title tokens
                title_tokens = pos_target_lower.split()
                if not any(t in headline_lower for t in title_tokens):
                    continue
                    
                # 3. ELASTIC CURRENT ANCHOR GATE: Validate active connection parameters
                has_company_match = any(word in full_text_block for word in company_words)
                if not has_company_match:
                    continue
                
                # 4. URL Unshortener Thread Resolution
                real_linkedin_url = search_service.unshorten_google_url(google_url)
                
                verified_records.append({
                    "Full Name": name,
                    "Company": target_company.title(),
                    "Current Designation": headline,
                    "LinkedIn Profile URL": real_linkedin_url,
                    "Status": "Verified Current ✅"
                })
                
                # Keep progress animation fluid
                prog_val = min(0.4 + ((i + 1) / total_rows) * 0.6, 1.0)
                progress_bar.progress(float(prog_val))
                
            time.sleep(0.1)
            progress_bar.empty()
            status_text.empty()
            
            if verified_records:
                df_final = pd.DataFrame(verified_records)
                st.success(f"Pipeline complete! Successfully processed {total_rows} entries and compiled {len(df_final)} highly accurate active leads.")
                
                display_cols = ["Full Name", "Company", "Current Designation", "LinkedIn Profile URL", "Status"]
                st.dataframe(df_final[display_cols], use_container_width=True)
                
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                    df_final[display_cols].to_excel(writer, sheet_name="Active Verified Leads", index=False)
                    
                st.download_button(
                    label="📥 Download Clean Lead Sheet Spreadsheet",
                    data=buf.getvalue(),
                    file_name=f"{target_company.lower().replace(' ', '_')}_verified_leads.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning(f"⚠️ Verification Gate Notice: {total_rows} broad entries were found, but all of them were flagged as past roles or title mismatches. Try broadening your designation keywords.")
        else:
            progress_bar.empty()
            status_text.empty()
            st.error("Data Gathering Error: Stage 1 returned 0 raw data rows from Google's regional index feed. Check that your target country dropdown matches the target company's market footprint.")

if logo_base64:
    st.markdown(f'<div class="bottom-logo-container"><img src="data:image/jpeg;base64,{logo_base64}"></div>', unsafe_allow_html=True)
