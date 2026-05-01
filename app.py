import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Privacy Automated Grader", page_icon="🛡️", layout="centered")

st.title("🛡️ Website Privacy Automated Grader")
st.markdown("Enter the URL of a website's privacy policy. The AI will scrape the text and grade it based on standard compliance pillars (Transparency, Consent, Data Minimization, and User Rights).")

# --- SIDEBAR (API KEY) ---
with st.sidebar:
    st.header("Configuration")
    st.markdown("To keep this tool free, it uses your personal Gemini API key.")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.markdown("[Get a free Gemini API key here](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    st.caption("This tool relies on public signals and policy text analysis. It does not perform back-end penetration testing.")

# --- MAIN INTERFACE ---
url_input = st.text_input("Privacy Policy URL", placeholder="https://www.example.com/privacy-policy")

if st.button("Run Privacy Audit"):
    # 1. Validation Checks
    if not api_key:
        st.warning("⚠️ Please enter your Gemini API Key in the sidebar to run the analysis.")
        st.stop()
    if not url_input.startswith("http"):
        st.warning("⚠️ Please enter a valid URL starting with http:// or https://")
        st.stop()

    # 2. Web Scraping
    with st.spinner("Scraping website text..."):
        try:
            # Use a generic User-Agent so websites don't immediately block the request
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url_input, headers=headers, timeout=15)
            response.raise_for_status() # Check for 404 or 500 errors
            
            # Parse HTML and extract plain text
            soup = BeautifulSoup(response.content, 'html.parser')
            for script in soup(["script", "style", "nav", "footer"]):
                script.extract() # Remove code and navigation menus
            scraped_text = soup.get_text(separator=' ', strip=True)
            
            # Truncate text slightly to ensure it fits in standard token limits
            scraped_text = scraped_text[:40000] 
            
        except Exception as e:
            st.error(f"Failed to scrape the URL. The website might have bot-protection. Error: {e}")
            st.stop()

    # 3. AI Analysis & Scoring
    with st.spinner("AI is auditing the policy against the tracker rubric..."):
        try:
            genai.configure(api_key=api_key)
            # Using the fast, efficient flash model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Act as an expert Data Privacy Auditor. Review the following privacy policy text scraped from a website and grade it based on the specific rubric below. 
            
            SCORING SYSTEM:
            0 = Not mentioned or highly non-compliant
            2 = Partially mentioned, vague, or unclear
            4 = Fully compliant, explicitly stated, and easy to understand

            RUBRIC CATEGORIES TO CHECK:
            1. Transparency & Clarity: Are data types clearly explained? Is the purpose explained simply? Is third-party sharing explicitly mentioned?
            2. Consent & User Choice: Is there a visible reject option? Is age-related consent mentioned?
            3. Data Collection & Minimization: Is sensitive data explained? 
            4. Tracking & Third-Party: Is tracking/cookie usage clearly disclosed? Is an opt-out available?
            5. User Rights & Grievance: Are user rights explained? Is there a clear contact for complaints/DPO?

            POLICY TEXT:
            {scraped_text}

            INSTRUCTIONS FOR OUTPUT:
            Provide a clean, professional Markdown report. Do not include the prompt in your response. 
            Include:
            - An Overall Score summary.
            - A breakdown of each of the 5 Rubric Categories. Give each category a score (0, 2, or 4) based on your average assessment of the checks within that category.
            - Provide a bulleted list of short "Notes" under each category justifying your score based *only* on the text provided.
            """
            
            response = model.generate_content(prompt)
            
            # 4. Display Results
            st.success("Audit Complete!")
            st.markdown("---")
            st.markdown(response.text)

        except Exception as e:
            st.error(f"AI Analysis failed. Check your API key. Error: {e}")