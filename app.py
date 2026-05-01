import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Privacy Automated Grader", page_icon="🛡️", layout="centered")

st.title("🛡️ Website Privacy Automated Grader")
st.markdown("Enter the URL of a website's privacy policy. The AI will scrape the text and grade it based on standard compliance pillars (Transparency, Consent, Data Minimization, and User Rights).")

# --- MAIN INTERFACE ---
url_input = st.text_input("Privacy Policy URL", placeholder="https://www.example.com/privacy-policy")

if st.button("Run Privacy Audit"):
    # 1. Validation Checks
    if not url_input.startswith("http"):
        st.warning("⚠️ Please enter a valid URL starting with http:// or https://")
        st.stop()

    # 2. Web Scraping
    with st.spinner("Scraping website text..."):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url_input, headers=headers, timeout=15)
            response.raise_for_status() 
            
            soup = BeautifulSoup(response.content, 'html.parser')
            for script in soup(["script", "style", "nav", "footer"]):
                script.extract() 
            scraped_text = soup.get_text(separator=' ', strip=True)
            scraped_text = scraped_text[:40000] 
            
        except Exception as e:
            st.error(f"Failed to scrape the URL. The website might have bot-protection. Error: {e}")
            st.stop()

    # 3. AI Analysis & Scoring
    with st.spinner("AI is auditing the policy against the tracker rubric..."):
        try:
            # FETCHING THE KEY FROM THE SECRETS VAULT
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            
            # THE FIX: Using the active, supported model
            model = genai.GenerativeModel('gemini-2.5-flash')
            
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

        except KeyError:
            st.error("⚠️ API Key Error: The app couldn't find the key. Ensure you saved it in Streamlit's settings as GEMINI_API_KEY.")
        except Exception as e:
            st.error(f"AI Analysis failed. Error: {e}")
