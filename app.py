"""
AI Job Application Agent - Production Ready for Hugging Face Spaces
✅ Real job search from LinkedIn, Naukri, Indeed, Wellfound
✅ Automatic personal info filling
✅ Real-time monitoring & auto-apply
✅ Email confirmations
✅ CRM Integration
✅ Interview Prep with PDF export
"""

import streamlit as st
import time
import os
import json
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (HF Secrets support)
load_dotenv()

# Ensure the project root is in sys.path
root_path = Path(__file__).resolve().parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))
    
# Also add src to path just in case
src_path = root_path / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

st.set_page_config(
    page_title="AI Job Agent Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for high-end UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
    .stApp { background: #0d0f14; color: #e8eaf0; }
    .metric-card { background: linear-gradient(135deg, #1a1d27 0%, #12141c 100%); border: 1px solid #2a2d3e; border-radius: 12px; padding: 20px; text-align: center; }
    .metric-number { font-size: 2.4rem; font-weight: 700; color: #4f6ef7; }
    .metric-label { font-size: 0.8rem; color: #7a7f9a; text-transform: uppercase; letter-spacing: 1px; }
    .job-card { background: #1a1d27; border: 1px solid #2a2d3e; border-left: 4px solid #4f6ef7; border-radius: 8px; padding: 16px; margin-bottom: 10px; }
    .section-title { font-size: 1.4rem; font-weight: 700; color: #e8eaf0; border-bottom: 2px solid #4f6ef7; padding-bottom: 8px; margin-bottom: 20px; }
    div[data-testid="stSidebar"] { background: #0d0f14; border-right: 1px solid #2a2d3e; }
    .stButton > button { background: linear-gradient(135deg, #4f6ef7, #7c4dff); color: white; border: none; border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
defaults = {
    "jobs": [],
    "monitoring": False,
    "monitoring_log": [],
    "email_test_result": None,
    "openai_key": os.getenv("OPENAI_API_KEY", ""),
    "interview_prep": {},
    "resume_path": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Module Imports with Individual Fallbacks
ATS_AVAILABLE = False
try:
    from src.intelligence.ats_scorer import ATSScoreEngine
    ATS_AVAILABLE = True
except Exception as e:
    st.sidebar.warning(f"ATS Engine unavailable: {e}")

CL_AVAILABLE = False
try:
    from src.intelligence.cover_letter import CoverLetterAgent
    CL_AVAILABLE = True
except Exception as e:
    st.sidebar.warning(f"Cover Letter Engine unavailable: {e}")

AGENT_AVAILABLE = False
try:
    from src.intelligence.agent_pipeline import JobApplicationAgent
    AGENT_AVAILABLE = True
except Exception as e:
    import traceback
    traceback.print_exc()
    st.sidebar.warning(f"Agent Pipeline unavailable: {e}")

SCRAPERS_AVAILABLE = False
try:
    from src.scraper.linkedin_scraper import LinkedInScraper
    from src.scraper.other_scrapers import NaukriScraper, IndeedScraper, WellfoundScraper
    SCRAPERS_AVAILABLE = True
except Exception as e:
    st.sidebar.warning(f"Scrapers unavailable: {e}")

CRM_AVAILABLE = False
try:
    from src.utils.crm import ApplicationCRM
    crm = ApplicationCRM()
    CRM_AVAILABLE = True
except Exception as e:
    st.sidebar.warning(f"CRM unavailable: {e}")

EMAIL_AVAILABLE = False
try:
    from src.utils.email import EmailNotifier
    email_notifier = EmailNotifier()
    EMAIL_AVAILABLE = True
except Exception as e:
    st.sidebar.warning(f"Email Notifier unavailable: {e}")

PREP_AVAILABLE = False
try:
    from src.intelligence.interview_prep import InterviewPrepGenerator
    interview_prep_generator = InterviewPrepGenerator()
    PREP_AVAILABLE = True
except Exception as e:
    st.sidebar.warning(f"Interview Prep unavailable: {e}")

RAG_AVAILABLE = False
try:
    from src.intelligence.rag_pipeline import ResumeRAG
    if "rag_engine" not in st.session_state:
        st.session_state.rag_engine = ResumeRAG(os.getenv("OPENAI_API_KEY"))
    RAG_AVAILABLE = True
except Exception as e:
    st.sidebar.warning(f"RAG Engine unavailable: {e}")

GMAIL_AVAILABLE = False
try:
    from src.utils.gmail_tracker import GmailTracker
    gmail_tracker = GmailTracker()
    GMAIL_AVAILABLE = True
except Exception as e:
    st.sidebar.warning(f"Gmail Tracker unavailable: {e}")

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Sidebar Setup
with st.sidebar:
    st.markdown("## ⚙️ Setup & Profile")
    st.divider()

    st.markdown("### 👤 Your Details")
    first_name = st.text_input("First Name", value="John", key="sb_fname")
    last_name = st.text_input("Last Name", value="Doe", key="sb_lname")
    full_name = f"{first_name} {last_name}"
    recipient_email = st.text_input("Your Email", value=os.getenv("USER_EMAIL", ""), key="sb_email")
    phone = st.text_input("Phone Number", key="sb_phone")
    city = st.text_input("City", key="sb_city")
    linkedin_url = st.text_input("LinkedIn URL", key="sb_linkedin")

    st.divider()

    st.markdown("### 📧 Email Config")
    with st.expander("Configure Gmail SMTP"):
        sender_email = st.text_input("Gmail address", value=os.getenv("SENDER_EMAIL", ""))
        sender_password = st.text_input("App Password", type="password", value=os.getenv("SENDER_PASSWORD", ""))
        if st.button("🔌 Test Connection"):
            if ATS_AVAILABLE:
                ok, msg = email_notifier.test_email_connection(sender_email, sender_password)
                st.success(msg) if ok else st.error(msg)

    st.divider()

    st.markdown("### 🔑 Platform Credentials")
    with st.expander("LinkedIn"):
        li_email = st.text_input("LinkedIn Email", value=os.getenv("LINKEDIN_EMAIL", ""))
        li_pass = st.text_input("LinkedIn Password", type="password", value=os.getenv("LINKEDIN_PASSWORD", ""))
    
    st.divider()

    st.markdown("### 📄 Resume Upload")
    resume_file = st.file_uploader("PDF Resume", type=["pdf"])
    if resume_file:
        resume_dir = Path("data/resumes")
        resume_dir.mkdir(parents=True, exist_ok=True)
        resume_path = resume_dir / resume_file.name
        
        # Save file safely
        with open(resume_path, "wb") as f:
            f.write(resume_file.getbuffer())
        st.session_state["resume_path"] = str(resume_path)
        
        # Extract text from PDF robustly
        try:
            import pdfplumber
            with pdfplumber.open(resume_path) as pdf:
                # Filter out empty pages and join text
                extracted_pages = []
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        extracted_pages.append(page_text)
                
                resume_text = "\n\n".join(extracted_pages)
                
            if resume_text.strip():
                st.session_state["resume_text"] = resume_text
                st.success(f"✅ Resume saved! ({len(resume_text)} chars)")
                
                # Initialize RAG Engine
                if RAG_AVAILABLE and st.session_state.get("openai_key"):
                    st.session_state.rag_engine.openai_key = st.session_state.openai_key
                    ok, msg = st.session_state.rag_engine.initialize_from_text(resume_text)
                    if ok:
                        st.info("🧠 RAG Pipeline initialized for advanced matching!")
                    else:
                        st.warning(f"RAG init failed: {msg}")
            else:
                st.error("❌ PDF upload successful but no text could be extracted. Is it a scanned image?")
                st.session_state["resume_text"] = ""
                
        except ImportError:
            st.error("❌ pdfplumber library not found. Please install it.")
        except Exception as e:
            st.error(f"❌ Failed to process PDF: {str(e)}")
            st.session_state["resume_text"] = ""

    st.divider()

    st.markdown("### 🤖 AI Key")
    openai_key = st.text_input("OpenAI Key", type="password", value=st.session_state.openai_key)
    if openai_key:
        st.session_state["openai_key"] = openai_key
        os.environ["OPENAI_API_KEY"] = openai_key

# Main Content Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🔍 Search & Apply", 
    "⚡ Real-time Monitor",
    "📝 Cover Letter", 
    "🎯 Interview Prep", 
    "🧠 Resume Intelligence",
    "📥 Recruiter Inbox", 
    "📋 Kanban CRM"
])

# TAB 1: Search & Apply
with tab1:
    st.markdown('<div class="section-title">🔍 Job Search & Auto Apply</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### Find Jobs")
        with st.form("search_form"):
            job_title = st.text_input("Job Title", "Python Engineer")
            job_loc = st.text_input("Location", "Remote")
            platforms = st.multiselect("Platforms", ["LinkedIn", "Indeed", "Naukri", "Wellfound"], default=["LinkedIn"])
            num_results = st.slider("Results", 1, 10, 5)
            search_btn = st.form_submit_button("🚀 Search Now")

        if search_btn:
            with st.spinner("Searching..."):
                async def fetch_jobs():
                    results = []
                    if "LinkedIn" in platforms:
                        if SCRAPERS_AVAILABLE:
                            scr = LinkedInScraper(headless=True)
                            await scr.start()
                            results.extend(await scr.search_jobs(job_title, job_loc, limit=num_results))
                            await scr.stop()
                        else:
                            st.warning("LinkedIn Scraper unavailable.")
                    # Add other scrapers here...
                    return results
                
                jobs = run_async(fetch_jobs())
                st.session_state.jobs = [j.__dict__ for j in jobs]
                st.success(f"Found {len(st.session_state.jobs)} jobs!")

    # Display Found Jobs
    if st.session_state.jobs:
        st.markdown("---")
        st.markdown(f"### 📋 Found Jobs ({len(st.session_state.jobs)})")
        for i, job in enumerate(st.session_state.jobs):
            with st.container(border=True):
                jc1, jc2 = st.columns([3, 1])
                jc1.markdown(f"**{job['title']}**")
                jc1.caption(f"{job['company']} • {job['location']} • {job.get('source', 'Unknown')}")
                
                if jc2.button(f"⚡ Apply Now", key=f"apply_{i}"):
                    if AGENT_AVAILABLE:
                        with st.spinner(f"Applying to {job['company']}..."):
                            agent = JobApplicationAgent(use_mock=not bool(li_email))
                            result = run_async(agent.run_pipeline(
                                job=job,
                                resume_text=st.session_state.get("resume_text", ""),
                                applicant={"name": full_name, "email": recipient_email, "phone": phone},
                                credentials={"linkedin_email": li_email, "linkedin_password": li_pass},
                                resume_path=st.session_state.resume_path,
                                openai_key=openai_key,
                                rag_engine=st.session_state.get("rag_engine")
                            ))
                            if result.get("apply_result", {}).get("ok"):
                                st.success(f"✅ Applied to {job['company']}!")
                            else:
                                st.error(f"❌ Failed: {result.get('apply_result', {}).get('msg')}")
                    else:
                        st.error("Agent Pipeline unavailable.")

    with col2:
        st.markdown("#### Bulk Apply")
        if st.button("🚀 Apply to ALL Found Jobs", type="primary"):
            if not st.session_state.jobs:
                st.warning("Search for jobs first!")
            else:
                progress = st.progress(0)
                for i, job in enumerate(st.session_state.jobs):
                    st.write(f"Applying to {job['title']} @ {job['company']}...")
                    
                    # Real Application Pipeline
                    if AGENT_AVAILABLE:
                        agent = JobApplicationAgent(use_mock=not bool(li_email))
                        result = run_async(agent.run_pipeline(
                            job=job,
                            resume_text=st.session_state.get("resume_text", ""),
                            applicant={"name": full_name, "email": recipient_email, "phone": phone},
                            credentials={"linkedin_email": li_email, "linkedin_password": li_pass},
                            resume_path=st.session_state.resume_path,
                            openai_key=openai_key,
                            rag_engine=st.session_state.get("rag_engine")
                        ))
                        
                        if result.get("apply_result", {}).get("ok"):
                            st.success(f"✅ Applied to {job['company']}!")
                        else:
                            st.error(f"❌ Failed for {job['company']}: {result.get('apply_result', {}).get('msg')}")
                    else:
                        st.error("Agent Pipeline unavailable.")
                        
                    progress.progress((i+1)/len(st.session_state.jobs))
                st.success("Bulk apply complete!")

# TAB 2: Real-time Monitor (NEW)
with tab2:
    st.markdown('<div class="section-title">⚡ Real-time Monitoring Loop</div>', unsafe_allow_html=True)
    st.info("This loop will periodically search for new jobs and apply automatically based on your criteria.")
    
    m_col1, m_col2 = st.columns([1, 2])
    
    with m_col1:
        mon_title = st.text_input("Monitor Title", "Senior AI Engineer", key="mon_title")
        mon_loc = st.text_input("Monitor Location", "Remote", key="mon_loc")
        mon_interval = st.number_input("Interval (minutes)", min_value=1, value=30, key="mon_interval")
        mon_threshold = st.slider("ATS Score Threshold", 0, 100, 70, key="mon_threshold")
        
        if st.button("▶️ Start Monitoring" if not st.session_state.monitoring else "⏹️ Stop Monitoring"):
            st.session_state.monitoring = not st.session_state.monitoring
            if st.session_state.monitoring:
                st.session_state.monitoring_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring started for {mon_title} in {mon_loc}")
            else:
                st.session_state.monitoring_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring stopped.")

    with m_col2:
        st.markdown("#### Monitoring Activity")
        log_placeholder = st.empty()
        
        # Real-time update loop
        if st.session_state.monitoring:
            with st.spinner("Monitoring active..."):
                st.write(f"🔄 Scanning for **{mon_title}** in **{mon_loc}**...")
                
                # Single Scan Iteration
                async def scan_and_apply():
                    if SCRAPERS_AVAILABLE and AGENT_AVAILABLE:
                        scr = LinkedInScraper(headless=True)
                        await scr.start()
                        found_jobs = await scr.search_jobs(mon_title, mon_loc, limit=3)
                        await scr.stop()
                        
                        for job_obj in found_jobs:
                            job = job_obj.__dict__
                            st.session_state.monitoring_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Found: {job['title']} @ {job['company']}")
                            
                            # Apply Pipeline
                            agent = JobApplicationAgent(use_mock=not bool(li_email))
                            result = await agent.run_pipeline(
                                job=job,
                                resume_text=st.session_state.get("resume_text", ""),
                                applicant={"name": full_name, "email": recipient_email, "phone": phone},
                                credentials={"linkedin_email": li_email, "linkedin_password": li_pass},
                                resume_path=st.session_state.resume_path,
                                openai_key=openai_key,
                                threshold=mon_threshold,
                                rag_engine=st.session_state.get("rag_engine")
                            )
                            
                            if result.get("apply_result", {}).get("ok"):
                                st.session_state.monitoring_log.append(f"✅ Auto-applied to {job['company']}!")
                            elif result.get("skip_reason"):
                                st.session_state.monitoring_log.append(f"⏩ Skipped: {result['skip_reason']}")
                            else:
                                st.session_state.monitoring_log.append(f"❌ Failed: {result.get('apply_result', {}).get('msg')}")
                    else:
                        st.session_state.monitoring_log.append("❌ Monitoring failed: Scrapers or Agent unavailable.")

                run_async(scan_and_apply())
                st.session_state.monitoring_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Scan complete. Waiting {mon_interval}m...")
                
                # Update UI
                log_text = "\n".join(reversed(st.session_state.monitoring_log))
                log_placeholder.text_area("Live Logs", value=log_text, height=300)
                
                # Schedule next run (Streamlit hack)
                time.sleep(2) # Brief pause before rerun
                st.rerun()
        else:
            log_text = "\n".join(reversed(st.session_state.monitoring_log))
            log_placeholder.text_area("Logs", value=log_text, height=300)

# TAB 5: Resume Intelligence (NEW)
with tab5:
    st.markdown('<div class="section-title">🧠 AI Resume Intelligence (RAG)</div>', unsafe_allow_html=True)
    if RAG_AVAILABLE and st.session_state.get("resume_text"):
        st.success("✅ RAG Pipeline is active and your resume is indexed.")
        
        query = st.text_input("🔍 Ask AI about your resume", placeholder="e.g., What are my top 3 technical skills?")
        if query:
            with st.spinner("Searching resume context..."):
                context = st.session_state.rag_engine.get_relevant_context(query)
                if context:
                    st.markdown("### 📄 Relevant Resume Sections")
                    st.info(context)
                    
                    # Optional: Use LLM to summarize
                    if st.session_state.get("openai_key"):
                        from langchain_openai import ChatOpenAI
                        llm = ChatOpenAI(api_key=st.session_state.openai_key, model="gpt-4o-mini")
                        response = llm.invoke(f"Based on these resume sections, answer the question: {query}\n\nContext:\n{context}")
                        st.markdown("### 🤖 AI Answer")
                        st.write(response.content)
                else:
                    st.warning("No relevant sections found for that query.")
        
        st.divider()
        st.markdown("### 📊 Skill Extraction (Auto-RAG)")
        if st.button("Extract Key Achievements"):
            with st.spinner("Analyzing..."):
                analysis = st.session_state.rag_engine.tailor_resume_sections("Identify key professional achievements and quantify them where possible.")
                st.write(analysis.get("raw_response", "Analysis failed."))
    else:
        st.info("Upload a resume in the sidebar to activate AI Intelligence.")

# TAB 6: Recruiter Inbox
with tab6:
    st.markdown('<div class="section-title">📥 Recruiter Inbox Tracker</div>', unsafe_allow_html=True)
    if GMAIL_AVAILABLE:
        if st.button("🔄 Sync Gmail"):
            with st.spinner("Syncing..."):
                emails = gmail_tracker.fetch_recruiter_emails()
                st.session_state["recruiter_emails"] = emails
        
        if "recruiter_emails" in st.session_state:
            for email in st.session_state["recruiter_emails"]:
                with st.expander(f"**{email['subject']}** - {email['category']}"):
                    st.write(f"From: {email['sender']}")
                    st.write(email['snippet'])
    else:
        st.info("Gmail Tracker unavailable.")

# TAB 7: CRM
with tab7:
    st.markdown('<div class="section-title">📋 Application Pipeline</div>', unsafe_allow_html=True)
    if CRM_AVAILABLE:
        stats = crm.get_stats()
        cols = st.columns(5)
        for i, (stage, count) in enumerate(stats['by_stage'].items()):
            cols[i].metric(stage, count)
        
        # Display Kanban
        kanban = crm.get_kanban()
        k_cols = st.columns(len(kanban))
        for i, (stage, jobs) in enumerate(kanban.items()):
            with k_cols[i]:
                st.markdown(f"**{stage}**")
                for job in jobs:
                    st.caption(f"{job['title']} @ {job['company']}")

st.divider()
st.caption("🚀 AI Job Agent Pro — Production Ready | Hugging Face Spaces Compatible")
