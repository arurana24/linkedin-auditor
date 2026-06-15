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

# ==========================================
# SYSTEM SETUP & LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

GOOGLE_API_KEY = st.secrets["GOOGLE_SEARCH_API_KEY"]
GOOGLE_CSE_ID = st.secrets["GOOGLE_CSE_CX_ID"]

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

def search_linkedin_professionals(company, position, num_results=10):
    """
    Executes a clean, accountless X-Ray lookup query targeting active, 
    CURRENT employees by utilizing context-aware Boolean operators.
    """
    search_query = f'site:linkedin.com/in/ "{company}" "{position}" "current" -intitle:past'
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": search_query,
        "num": min(num_results, 10)
    }
    
    try:
        time.sleep(random.uniform(0.2, 0.5))
        response = requests.get(url, params=params).json()
        search_items = response.get("items", [])
        
        records = []
        for item in search_items:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            profile_url = item.get("link", "")
            
            if "past:" in snippet.lower() or "former" in snippet.lower():
                if f"current: {company.lower()}" not in snippet.lower() and f"at {company.lower()}" not in snippet.lower():
                    continue
            
            clean_name = title.split("-")[0].split("|")[0].strip()
            
            records.append({
                "Target Company": company,
                "Target Designation": position,
                "Professional Name": clean_name,
                "Current Title Line": title,
                "Profile Link": profile_url,
                "Public Snippet Summary": snippet
            })
        return records
    except Exception as e:
        logging.error(f"Search API Layer Connection Fail: {str(e)}")
        return []

# ==========================================
# STREAMLIT USER INTERFACE VIEW LAYER
# ==========================================
st.title("LinkedIn Personnel Identification Matrix")
st.markdown("Extract public URLs and identifying details for current corporate professionals based on multi-designation targeting benchmarks.")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 1. Target Configurations")
    target_company = st.text_input("Target Company Name:", value="Google")
    
    st.markdown("##### Designations List (Max 10)")
    
    # Clean fallback dataframe layout initialization
    default_df = pd.DataFrame([
        {"Designations": "Product Manager"},
        {"Designations": "Software Engineer"},
        {"Designations": ""}
    ])
    
    # Render data_editor cleanly without mapping state assignments around it
    edited_df = st.data_editor(
        default_df, 
        num_rows="dynamic", 
        max_rows=10, 
        use_container_width=True,
        key="designations_editor_instance"
    )

with col_right:
    st.markdown("### 2. Execution Toggles")
    result_depth = st.slider("Results Depth Limit per Designation:", min_value=5, max_value=10, value=10)
    st.info(
        "💡 **Query Processing Note:**\n"
        "The engine applies Boolean string modifiers ('current' / '-intitle:past') "
        "and checks result layouts to skip past employees automatically."
    )

if st.button("Run Personnel Target Search", type="primary"):
    # Extract row items directly from the active widget instance safely during button submit execution
    raw_designations = edited_df["Designations"].dropna().tolist()
    active_designations = [str(d).strip() for d in raw_designations if str(d).strip() != ""]
    
    if not target_company:
        st.error("Please provide a valid Target Company Name.")
    elif not active_designations:
        st.error("Please input at least one Designation in the table list.")
    else:
        all_results_pool = []
        p_bar = st.progress(0)
        status_text = st.empty()
        
        total_steps = len(active_designations)
        
        for idx, position in enumerate(active_designations):
            status_text.text(f"Querying indexing logs for: {position} at {target_company}...")
            records = search_linkedin_professionals(target_company, position, result_depth)
            all_results_pool.extend(records)
            p_bar.progress((idx + 1) / total_steps)
            
        status_text.empty()
        
        if all_results_pool:
            df_linkedin = pd.DataFrame(all_results_pool)
            st.success(f"Successfully mapped {len(df_linkedin)} current professionals across your targets.")
            st.dataframe(df_linkedin, use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df_linkedin.to_excel(writer, index=False, sheet_name="LinkedIn Current Leads")
                
            st.download_button(
                label="Download Current LinkedIn Target Workbook",
                data=buf.getvalue(),
                file_name=f"{target_company.lower()}_current_personnel_leads.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No active current records matched your specific filter targets.")

if logo_base64:
    st.markdown(f'<div class="bottom-logo-container"><img src="data:image/jpeg;base64,{logo_base64}"></div>', unsafe_allow_html=True)
