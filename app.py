import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
import google.generativeai as genai

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Jurisdictional Privacy Auditor", page_icon="🛡️", layout="centered")

st.title("🛡️ Jurisdictional Privacy Auditor")
st.markdown("Scan any domain for privacy compliance gaps based on specific regional data protection laws.")

# --- MAIN INTERFACE ---
col1, col2 = st.columns([3, 1])

with col1:
    url_input = st.text_input("Website or Privacy Policy URL", placeholder="example.com", label_visibility="collapsed")
with col2:
    framework = st.selectbox(
        "Regulatory Framework", 
        ["Universal", "GDPR (Europe)", "DPDPA (India)", "PDPL (Middle East)", "HIPAA (US Health)"],
        label_visibility="collapsed"
    )

if st.button("Run Compliance Audit"):
    
    # --- NEW URL CLEANER ---
    url_input = url_input.strip()
    if not url_input:
        st.warning("⚠️ Please enter a domain or URL to begin.")
        st.stop()
        
    # If the user forgot http:// or https://, add it automatically
    if not url_input.startswith("http://") and not url_input.startswith("https://"):
        url_input = "https://" + url_input

    # 2. Web Scraping & Auto-Discovery
    with st.spinner(f"Hunting for policy and preparing for {framework} audit..."):
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
                    st.info(f"🔍 Auto-detected Policy: {target_url}")
                    
                    response = requests.get(target_url, headers=headers, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')

            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract() 
            scraped_text = soup.get_text(separator=' ', strip=True)
            scraped_text = scraped_text[:40000] 

            if len(scraped_text) < 300:
                st.warning("⚠️ The scraped text is very short. Ensure this is the actual policy.")

        except Exception as e:
            st.error(f"Failed to scrape the URL. Ensure the website exists. Error: {e}")
            st.stop()

    # 3. AI Analysis & Dynamic Scoring
    with st.spinner(f"AI is auditing against {framework} requirements..."):
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            framework_instructions = {
                "Universal": "Evaluate based on general global privacy best practices.",
                "GDPR (Europe)": "Evaluate STRICTLY against the General Data Protection Regulation (GDPR). You must actively look for and flag missing explicit opt-in consent, Right to be Forgotten mechanisms, 72-hour breach notification policies, and Data Protection Officer (DPO) contact details.",
                "DPDPA (India)": "Evaluate STRICTLY against India's Digital Personal Data Protection Act (DPDPA). You must actively look for and flag missing verifiable parental consent for children, mentions of Consent Managers, duties of Data Principals, and clear notice requirements.",
                "PDPL (Middle East)": "Evaluate STRICTLY against the Saudi/Middle Eastern Personal Data Protection Laws (PDPL). You must actively look for explicit consent requirements and details regarding cross-border data transfers and data localization.",
                "HIPAA (US Health)": "Evaluate STRICTLY against the Health Insurance Portability and Accountability Act (HIPAA). You must actively look for Notice of Privacy Practices (NPP), Business Associate Agreements (BAAs), and strict protections for Protected Health Information (PHI)."
            }
            
            specific_instruction = framework_instructions[framework]
            
            prompt = f"""
            Act as an expert Data Privacy Auditor and Legal Analyst. Review the following privacy policy text.
            
            YOUR OBJECTIVE: 
            Audit this text specifically for compliance with: {framework}.
            {specific_instruction}

            SCORING SYSTEM:
            0 = Missing, highly non-compliant, or violates the specified framework.
            2 = Vague, partial compliance, or legally ambiguous.
            4 = Fully compliant, explicit, and legally sound for the specified framework.

            RUBRIC CATEGORIES TO CHECK:
            1. Transparency & Lawful Basis: Is the purpose of collection legally justified under the selected framework?
            2. Consent & User Choice: Are the consent mechanisms compliant with the selected framework's specific strictness (e.g., GDPR opt-in vs universal opt-out)?
            3. Data Collection & Minimization: Is sensitive data defined and handled correctly according to the selected framework?
            4. Tracking & Third-Party: Are third-party transfers and cookie compliance clearly disclosed?
            5. User Rights & Grievance: Are the specific legal rights (e.g., erasure, portability) and mandated grievance officers mentioned?

            POLICY TEXT:
            {scraped_text}

            INSTRUCTIONS FOR OUTPUT:
            Provide a clean, professional Markdown report.
            - Include an Overall Score out of 20.
            - Give a brief executive summary of how it holds up against the {framework}.
            - Break down the 5 Rubric Categories with scores and bulleted notes justifying the score based on the text and the law.
            """
            
            response = model.generate_content(prompt)
            
            # 4. Display Results
            st.success(f"{framework} Audit Complete!")
            st.markdown("---")
            st.markdown(response.text)

        except KeyError:
            st.error("⚠️ API Key Error: The app couldn't find the key in Streamlit Secrets.")
        except Exception as e:
            st.error(f"AI Analysis failed. Error: {e}")
