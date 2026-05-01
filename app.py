import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
import google.generativeai as genai

# --- UI CONFIGURATION & STYLING ---
st.set_page_config(page_title="Enterprise Privacy Auditor", page_icon="🛡️", layout="centered")

# Custom CSS for a cleaner, enterprise look
st.markdown("""
    <style>
    .main-header {font-size: 2.5rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0px;}
    .sub-header {font-size: 1.1rem; color: #4B5563; margin-bottom: 30px;}
    .stButton>button {width: 100%; font-weight: bold; background-color: #1E3A8A; color: white;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🛡️ Enterprise Privacy Auditor</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Automated compliance scanning and remediation roadmapping.</p>', unsafe_allow_html=True)

with st.expander("ℹ️ How this tool works (Click to expand)"):
    st.write("This tool scans public web domains against major data protection regulations. It utilizes AI to read the publicly available privacy policy, grades it out of 100 based on standard legal pillars, and generates a tailored software and consulting roadmap to fix identified gaps.")

st.divider()

# --- MAIN INTERFACE ---
col1, col2 = st.columns([3, 1])

with col1:
    url_input = st.text_input("Target Domain or Policy URL", placeholder="example.com", label_visibility="collapsed")
with col2:
    framework = st.selectbox(
        "Regulatory Framework", 
        ["Universal", "GDPR (Europe)", "DPDPA (India)", "PDPL (Middle East)", "HIPAA (US Health)"],
        label_visibility="collapsed"
    )

if st.button("Run Enterprise Audit"):
    
    url_input = url_input.strip()
    if not url_input:
        st.warning("⚠️ Please enter a domain or URL to begin.")
        st.stop()
        
    if not url_input.startswith("http://") and not url_input.startswith("https://"):
        url_input = "https://" + url_input

    # 2. Web Scraping & Auto-Discovery
    with st.spinner(f"Scanning domain and locating legal documents for {framework} audit..."):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url_input, headers=headers, timeout=15)
            response.raise_for_status() 
            soup = BeautifulSoup(response.content, 'html.parser')

            target_url = url_input
            if url_input.count('/') <= 3 or url_input.endswith('/'):
                privacy_tag = soup.find('a', string=lambda text: text and 'privacy' in text.lower())
                if not privacy_tag: 
                    privacy_tag = soup.find('a', href=lambda href: href and 'privacy' in href.lower())
                
                if privacy_tag and privacy_tag.has_attr('href'):
                    target_url = urllib.parse.urljoin(url_input, privacy_tag['href'])
                    st.info(f"🔗 Target Policy Located: {target_url}")
                    
                    response = requests.get(target_url, headers=headers, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')

            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract() 
            scraped_text = soup.get_text(separator=' ', strip=True)
            scraped_text = scraped_text[:40000] 

            if len(scraped_text) < 300:
                st.warning("⚠️ The scraped text is suspiciously short. Ensure this domain has a public policy.")

        except Exception as e:
            st.error(f"Failed to reach the domain. Ensure the website exists and does not aggressively block bots. Error: {e}")
            st.stop()

    # 3. AI Analysis & Dynamic Scoring
    with st.spinner(f"Analyzing legal text and generating remediation roadmap..."):
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            framework_instructions = {
                "Universal": "Evaluate based on general global privacy best practices.",
                "GDPR (Europe)": "Evaluate STRICTLY against the General Data Protection Regulation (GDPR).",
                "DPDPA (India)": "Evaluate STRICTLY against India's Digital Personal Data Protection Act (DPDPA).",
                "PDPL (Middle East)": "Evaluate STRICTLY against the Saudi/Middle Eastern Personal Data Protection Laws (PDPL).",
                "HIPAA (US Health)": "Evaluate STRICTLY against the Health Insurance Portability and Accountability Act (HIPAA)."
            }
            specific_instruction = framework_instructions[framework]
            
            # --- THE NEW STRATEGIC PROMPT ---
            prompt = f"""
            Act as an expert Data Privacy Auditor, Compliance Consultant, and SaaS Solutions Architect. 
            Review the following privacy policy text.
            
            YOUR OBJECTIVE: 
            Audit this text specifically for compliance with: {framework}.
            {specific_instruction}

            SCORING SYSTEM (Out of 100):
            There are 5 categories. Grade each category out of 20 points:
            0 = Missing or highly non-compliant.
            10 = Vague, partial compliance, or legally ambiguous.
            20 = Fully compliant, explicit, and legally sound.

            CATEGORIES:
            1. Transparency & Lawful Basis
            2. Consent & User Choice
            3. Data Collection & Minimization
            4. Tracking & Third-Party Sharing
            5. User Rights & Grievance Mechanism

            POLICY TEXT:
            {scraped_text}

            INSTRUCTIONS FOR OUTPUT:
            Provide a clean, highly professional Markdown report tailored for a C-Level executive.
            
            Include the following sections exactly:
            
            # 📊 Executive Audit Summary
            - State the Overall Score prominently (e.g., **Final Compliance Score: 40 / 100**).
            - Provide a brief 2-sentence summary of their current risk level based on the {framework}.

            # 🔍 Category Breakdown
            - List each of the 5 categories with its score out of 20.
            - Provide 1-2 bullet points explaining exactly why they lost points based *only* on the text provided.

            # 🚀 Recommended Solution Roadmap
            Based on the specific gaps you found in the breakdown above, provide a 3-step actionable roadmap to achieve full compliance. You MUST weave the following recommendations into the steps where technically appropriate:
            - Mention leveraging enterprise data privacy automation platforms, specifically recommending **GoTrust** (for data security, privacy assessments, and governance automation) or **OneTrust** to automate technical gaps like Consent Management, Data Subject Requests (DSRs), or Data Mapping.
            - Recommend engaging a specialized legal privacy consulting firm or legal counsel to formally draft or overhaul their privacy policy if the text itself is missing, severely outdated, or legally vulnerable. Make this sound like a strategic imperative to avoid regulatory fines.
            """
            
            response = model.generate_content(prompt)
            
            # 4. Display Results in a stylized container
            st.success("✅ Audit & Remediation Plan Generated!")
            st.markdown("---")
            st.markdown(response.text)

        except KeyError:
            st.error("⚠️ API Key Error: The app couldn't find the key in Streamlit Secrets.")
        except Exception as e:
            st.error(f"AI Analysis failed. Error: {e}")
