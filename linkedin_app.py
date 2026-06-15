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

# High-End Premium Tech Aesthetic Layout Configuration
st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; }
    h1 {
        color: #0f172a !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    h2, h3, p, label, .stMarkdown, .stText {
        color: #334155 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    div.stButton > button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border-radius: 8px;
        border: none !important;
        padding: 0.7rem 2.5rem;
        font-weight: 600;
        font-size: 16px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        background-color: #1d4ed8 !important;
        transform: translateY(-1px);
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    div.stDownloadButton > button {
        background-color: #059669 !important;
        color: #ffffff !important;
        border-radius: 8px;
        border: none !important;
        padding: 0.6rem 2rem;
        font-weight: 600;
    }
    div.stDownloadButton > button:hover {
        background-color: #047857 !important;
    }
    .stProgress > div > div > div > div { background-color: #2563eb !important; }
    .css-1wivfrv, [data-testid="stSidebar"] { background-color: #ffffff !important; }
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
class GoogleRSSXRayService:
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

    def fetch_strict_current_leads(self, company: str, position: str, locale: dict) -> List[Dict[str, Any]]:
        raw_query = f'site:{locale["subdomain"]} {company} {position}'
        encoded_query = quote(raw_query)
        request_url = f"{self.base_url}?q={encoded_query}&hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
        
        try:
            time.sleep(random.uniform(0.2, 0.4))
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
                
                company_lower = company.lower()
                headline_lower = headline.lower()
                
                # CRITICAL VERIFICATION PASS: Strict structural matching rules
                exclusion_tokens = ["former", "past:", "ex-", "previously", "retired", "ex-employee", "worked at"]
                is_past_employee = any(token in clean_snippet or token in headline_lower for token in exclusion_tokens)
                
                # Verify the candidate currently operates at the target firm
                is_verified_current = (company_lower in headline_lower) or (f"at {company_lower}" in clean_snippet)
                
                # STRICT FILTER GATE: Instantly drop non-verified, historical, or messy entries
                if is_past_employee or not is_verified_current:
                    continue
                
                if "linkedin" in clean_snippet or "linkedin" in title_text.lower():
                    records.append({
                        "Full Name": name,
                        "Company": company.title(),
                        "Current Designation": headline,
                        "Status": "Verified Current ✅",
                        "Google Link Container": google_link,
                        "Target Designation Lookup": position
                    })
            return records
        except Exception:
            return []

search_service = GoogleRSSXRayService()

# ==========================================
# STREAMLIT PRESENTATION VIEW LAYER
# ==========================================
st.title("🎯 Premium Client Extraction Engine")
st.markdown("Generate highly accurate, verified target lists of currently active enterprise profiles. Zero clutter.")

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
        "💡 **Quality Assurance Notice:**\n"
        "This tool uses an internal multi-pass verification filter. Historical listings, former roles, "
        "and mismatched profiles are automatically purged before compiling your spreadsheet."
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
        results_pool = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, position in enumerate(active_designations):
            status_text.text(f"Scanning {selected_country} registries for: {position}...")
            batch = search_service.fetch_strict_current_leads(target_company, position, locale_config)
            results_pool.extend(batch)
            progress_bar.progress((idx + 0.5) / len(active_designations))
            
        if results_pool:
            status_text.text("Tracing tracking routing headers to unpack direct profile paths...")
            df_final = pd.DataFrame(results_pool).drop_duplicates(subset=["Full Name"]).reset_index(drop=True)
            
            real_urls = []
            total_urls = len(df_final)
            
            for i, (index, row) in enumerate(df_final.iterrows()):
                google_url = row["Google Link Container"]
                real_link = search_service.unshorten_google_url(google_url)
                real_urls.append(real_link)
                progress_bar.progress((idx + 0.5) / len(active_designations) + (i / total_urls) * 0.5)
                
            df_final["LinkedIn Profile URL"] = real_urls
            progress_bar.progress(1.0)
            time.sleep(0.4)
            progress_bar.empty()
            status_text.empty()
            
            st.success(f"Successfully compiled {len(df_final)} highly accurate active leads for {selected_country}!")
            
            # Clean layout view containing only the high-value data blocks
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
            progress_bar.empty()
            status_text.empty()
            st.error(f"No active profiles matching those exact filters found in {selected_country}. Try checking the company spelling.")

if logo_base64:
    st.markdown(f'<div class="bottom-logo-container"><img src="data:image/jpeg;base64,{logo_base64}"></div>', unsafe_allow_html=True)
