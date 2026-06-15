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

    @staticmethod
    def extract_company_name(headline: str, snippet: str, target_company: str) -> str:
        """
        Uses pattern parsing to pull out the most likely current company name from text.
        """
        combined_text = f"{headline} {snippet}"
        
        # If it's already verified current, return the target company directly
        if target_company.lower() in combined_text.lower():
            return target_company.title()
            
        # Regex check for patterns like "at CompanyName", "Current: CompanyName", or "Role - CompanyName"
        patterns = [
            r"current:\s*([^·\-\|\.\n]+)",
            r"\bat\s+([^·\-\|\.\n]+)",
            r"-\s*([^·\-\|\.\n]+)",
            r"\|\s*([^·\-\|\.\n]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # Clean up generic tail words
                extracted = re.sub(r'\s*(linkedin|profile|india|united states|uk|unverified).*$', '', extracted, flags=re.IGNORECASE)
                if len(extracted) > 2 and not any(x in extracted.lower() for x in ["former", "past", "manager", "director", "lead"]):
                    return extracted.title()
                    
        return "Unknown / External Entity"

    def unshorten_google_url(self, google_url: str) -> str:
        try:
            response = requests.head(google_url, headers=self.headers, allow_redirects=True, timeout=5.0)
            final_url = response.url.split("?")[0]
            if "linkedin.com/in/" in final_url:
                return final_url
            return google_url
        except Exception:
            return google_url

    def fetch_country_targeted_leads(self, company: str, position: str, locale: dict) -> List[Dict[str, Any]]:
        raw_query = f'site:{locale["subdomain"]} {company} {position}'
        encoded_query = quote(raw_query)
        
        request_url = f"{self.base_url}?q={encoded_query}&hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
        
        try:
            time.sleep(random.uniform(0.2, 0.5))
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
                
                exclusion_tokens = ["former", "past:", "ex-", "previously", "retired", "ex-employee", "worked at"]
                is_past_employee = any(token in clean_snippet or token in headline_lower for token in exclusion_tokens)
                
                if is_past_employee:
                    verification_status = "Unverified / Past Role ⚠️"
                    sort_order = 2
                elif company_lower in headline_lower or company_lower in clean_snippet:
                    verification_status = "Verified Current ✅"
                    sort_order = 0
                else:
                    verification_status = "Potential Match 🤔"
                    sort_order = 1
                
                # Run the new tracking text extractor pass
                current_company_detected = self.extract_company_name(headline, clean_snippet, company)
                
                if "linkedin" in clean_snippet or "linkedin" in title_text.lower():
                    records.append({
                        "Target Company": company,
                        "Target Designation": position,
                        "Professional Name": name,
                        "Current Profile Headline": headline,
                        "Detected Current Company": current_company_detected,
                        "Google Link Container": google_link,
                        "Employment Verification": verification_status,
                        "sort_order": sort_order
                    })
            return records
        except Exception:
            return []

search_service = GoogleRSSXRayService()

# ==========================================
# STREAMLIT PRESENTATION VIEW LAYER
# ==========================================
st.title("Automated Client Extraction Matrix")
st.markdown("Extract country-focused profiles with smart sorting and automated company tracking. 100% Free.")

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
        "🛡️ **System Infrastructure Status: Company Parsing Engine Active**\n"
        "The system now auto-analyzes profile snippet strings to catch the specific organization names where potential leads are active right now."
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
            
            df_final = df_final.sort_values(by="sort_order").reset_index(drop=True)
            
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
            
            st.success(f"Pipeline executed successfully. Synchronized {len(df_final)} matching profiles for {selected_country}.")
            
            # Reordered to show the new "Detected Current Company" column right in your primary dashboard view!
            display_cols = ["Professional Name", "Detected Current Company", "Current Profile Headline", "True LinkedIn Profile URL", "Employment Verification", "Target Designation"]
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
            st.error(f"No matching data streams found for {selected_country}. Try checking the company spelling.")

if logo_base64:
    st.markdown(f'<div class="bottom-logo-container"><img src="data:image/jpeg;base64,{logo_base64}"></div>', unsafe_allow_html=True)
