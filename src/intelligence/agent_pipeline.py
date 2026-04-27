import asyncio
import sys
from typing import TypedDict, Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except (ImportError, Exception):
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from intelligence.ats_scorer import ATSScoreEngine
    from intelligence.cover_letter import CoverLetterAgent
    from scraper.linkedin_scraper import LinkedInScraper
    from scraper.other_scrapers import NaukriScraper, IndeedScraper, WellfoundScraper
except ImportError:
    from .ats_scorer import ATSScoreEngine
    from .cover_letter import CoverLetterAgent
    from ..scraper.linkedin_scraper import LinkedInScraper
    from ..scraper.other_scrapers import NaukriScraper, IndeedScraper, WellfoundScraper


class AgentState(TypedDict):
    job: Dict[str, Any]
    resume_text: str
    applicant: Dict[str, Any]
    credentials: Dict[str, str]
    resume_path: str
    ats_score: int
    ats_breakdown: Dict[str, Any]
    tailored_resume: str
    cover_letter: str
    apply_result: Dict[str, Any]
    email_sent: bool
    skip_reason: str
    threshold: int
    suggestions: List[str]
    openai_key: Optional[str]
    rag_engine: Any # Using Any to avoid circular import or complex typing


class JobApplicationAgent:
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        self.ats_engine = ATSScoreEngine()
        
        self.linkedin_scraper = LinkedInScraper()
        self.naukri_scraper = NaukriScraper()
        self.indeed_scraper = IndeedScraper()
        self.wellfound_scraper = WellfoundScraper()
        
        if self.use_mock:
            self.linkedin_scraper.mock_mode = True
            self.naukri_scraper.mock_mode = True
            self.indeed_scraper.mock_mode = True
            self.wellfound_scraper.mock_mode = True

    async def research_node(self, state: AgentState) -> AgentState:
        job = state.get("job", {})
        url = job.get("url", "")
        
        if url and not self.use_mock:
            try:
                source = job.get("source", "LinkedIn")
                if source == "LinkedIn":
                    await self.linkedin_scraper.start()
                    description = await self.linkedin_scraper.get_job_description(url)
                    if description:
                        job["desc"] = description
                    await self.linkedin_scraper.stop()
            except Exception as e:
                pass
        
        if "desc" not in job or not job["desc"]:
            job["desc"] = self._get_default_jd()
        
        state["job"] = job
        return state

    async def ats_node(self, state: AgentState) -> AgentState:
        resume_text = state.get("resume_text", "")
        job = state.get("job", {})
        jd_text = job.get("desc", "")
        
        if resume_text and jd_text:
            self.ats_engine.load_resume(resume_text)
            score, breakdown = self.ats_engine.calculate_score(jd_text)
            suggestions = self.ats_engine.suggest_improvements(score, breakdown)
            
            state["ats_score"] = score
            state["ats_breakdown"] = breakdown
            state["suggestions"] = suggestions
        
        return state

    def decision_node(self, state: AgentState) -> str:
        score = state.get("ats_score", 0)
        threshold = state.get("threshold", 60)
        
        if score >= threshold:
            return "tailor"
        else:
            state["skip_reason"] = f"ATS score {score} below threshold {threshold}"
            return "skip"

    async def tailor_node(self, state: AgentState) -> AgentState:
        resume_text = state.get("resume_text", "")
        job = state.get("job", {})
        jd_text = job.get("desc", "")
        openai_key = state.get("openai_key")
        rag_engine = state.get("rag_engine") # Add RAG engine to state
        
        tailored_resume = resume_text
        
        if resume_text and jd_text:
            # Use RAG to get most relevant context if available
            context = ""
            if rag_engine:
                context = rag_engine.get_relevant_context(jd_text, k=5)
            
            self.ats_engine.load_resume(resume_text)
            
            bullets = self._extract_bullets(resume_text)
            if bullets:
                # If we have RAG context, we can pass it to the rewrite_bullets method
                # For now, we'll keep the existing method but we could enhance it later
                rewritten = self.ats_engine.rewrite_bullets(bullets, jd_text, openai_key)
                tailored_resume = self._replace_bullets(resume_text, bullets, rewritten)
            else:
                parsed = self.ats_engine.parse_jd(jd_text)
                keywords = parsed.required_skills + parsed.nice_to_have
                missing_keywords = [k for k in keywords if k.lower() not in resume_text.lower()]
                
                if missing_keywords:
                    keyword_str = ", ".join(missing_keywords[:5])
                    if "Skills:" in tailored_resume:
                        tailored_resume = tailored_resume.replace(
                            "Skills:", 
                            f"Skills: {keyword_str}, "
                        )
        
        state["tailored_resume"] = tailored_resume
        return state

    async def cover_letter_node(self, state: AgentState) -> AgentState:
        applicant = state.get("applicant", {})
        job = state.get("job", {})
        tailored_resume = state.get("tailored_resume", state.get("resume_text", ""))
        openai_key = state.get("openai_key")
        rag_engine = state.get("rag_engine")
        
        name = applicant.get("name", "Applicant")
        company = job.get("company", "Company")
        title = job.get("title", "Position")
        jd = job.get("desc", "")
        
        # Use RAG to find the most relevant achievements for this specific job
        context = ""
        if rag_engine and jd:
            context = rag_engine.get_relevant_context(jd, k=3)
        
        cl_agent = CoverLetterAgent(openai_key)
        # Pass the RAG context to the generator for much better personalization
        input_text = f"Resume:\n{tailored_resume[:1000]}\n\nMost Relevant Context from Resume:\n{context}"
        cover_letter = cl_agent.generate(name, company, title, jd, input_text)
        
        state["cover_letter"] = cover_letter
        return state

    async def apply_node(self, state: AgentState) -> AgentState:
        job = state.get("job", {})
        applicant = state.get("applicant", {})
        resume_path = state.get("resume_path", "")
        source = job.get("source", "LinkedIn")
        
        apply_result = {"ok": False, "msg": "", "ts": datetime.now().isoformat()}
        
        if self.use_mock:
            await asyncio.sleep(2)
            apply_result = {"ok": True, "msg": "Mock application submitted", "ts": datetime.now().isoformat()}
        else:
            try:
                if source == "LinkedIn":
                    await self.linkedin_scraper.start()
                    success, msg = await self.linkedin_scraper.easy_apply(
                        job, applicant, resume_path
                    )
                    await self.linkedin_scraper.stop()
                    apply_result = {"ok": success, "msg": msg, "ts": datetime.now().isoformat()}
                elif source == "Naukri":
                    success, msg = await self.naukri_scraper.apply_to_job(job, applicant, resume_path)
                    apply_result = {"ok": success, "msg": msg, "ts": datetime.now().isoformat()}
                elif source == "Indeed":
                    success, msg = await self.indeed_scraper.apply_to_job(job, applicant, resume_path)
                    apply_result = {"ok": success, "msg": msg, "ts": datetime.now().isoformat()}
                elif source == "Wellfound":
                    success, msg = await self.wellfound_scraper.apply_to_job(job, applicant, resume_path)
                    apply_result = {"ok": success, "msg": msg, "ts": datetime.now().isoformat()}
            except Exception as e:
                apply_result = {"ok": False, "msg": str(e), "ts": datetime.now().isoformat()}
        
        state["apply_result"] = apply_result
        return state

    async def notify_node(self, state: AgentState) -> AgentState:
        state["email_sent"] = True
        return state

    async def skip_node(self, state: AgentState) -> AgentState:
        return state

    def _extract_bullets(self, text: str) -> List[str]:
        bullets = []
        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('•') or stripped.startswith('-'):
                bullets.append(stripped.lstrip('•- ').strip())
        return bullets

    def _replace_bullets(self, text: str, original: List[str], rewritten: List[str]) -> str:
        lines = text.split('\n')
        new_lines = []
        bullet_idx = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('•') or stripped.startswith('-'):
                if bullet_idx < len(rewritten):
                    indent = line[:len(line) - len(stripped)]
                    new_lines.append(f"{indent}• {rewritten[bullet_idx]}")
                    bullet_idx += 1
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)

    def _get_default_jd(self) -> str:
        return """
        We are looking for an experienced software engineer to join our team.
        
        Requirements:
        - 3+ years of experience
        - Python programming
        - Web development experience
        - Cloud computing knowledge
        - Bachelor's degree in Computer Science
        
        Nice to have:
        - Machine learning experience
        - DevOps skills
        """

    def build_graph(self) -> Any:
        if LANGGRAPH_AVAILABLE:
            workflow = StateGraph(AgentState)
            
            workflow.add_node("research", self.research_node)
            workflow.add_node("ats", self.ats_node)
            workflow.add_node("tailor", self.tailor_node)
            workflow.add_node("cover_letter", self.cover_letter_node)
            workflow.add_node("apply", self.apply_node)
            workflow.add_node("notify", self.notify_node)
            workflow.add_node("skip", self.skip_node)
            
            workflow.set_entry_point("research")
            
            workflow.add_edge("research", "ats")
            workflow.add_conditional_edges(
                "ats",
                self.decision_node,
                {
                    "tailor": "tailor",
                    "skip": "skip"
                }
            )
            workflow.add_edge("tailor", "cover_letter")
            workflow.add_edge("cover_letter", "apply")
            workflow.add_edge("apply", "notify")
            workflow.add_edge("notify", END)
            workflow.add_edge("skip", END)
            
            return workflow.compile()
        else:
            return None

    async def run_pipeline(
        self,
        job: Dict,
        resume_text: str,
        applicant: Dict,
        credentials: Dict = None,
        resume_path: str = "",
        threshold: int = 60,
        openai_key: Optional[str] = None,
        rag_engine: Any = None
    ) -> Dict:
        initial_state: AgentState = {
            "job": job,
            "resume_text": resume_text,
            "applicant": applicant,
            "credentials": credentials or {},
            "resume_path": resume_path,
            "ats_score": 0,
            "ats_breakdown": {},
            "tailored_resume": "",
            "cover_letter": "",
            "apply_result": {},
            "email_sent": False,
            "skip_reason": "",
            "threshold": threshold,
            "suggestions": [],
            "openai_key": openai_key,
            "rag_engine": rag_engine
        }
        
        graph = self.build_graph()
        
        if graph and LANGGRAPH_AVAILABLE:
            result = await graph.ainvoke(initial_state)
            return result
        else:
            state = initial_state.copy()
            state = await self.research_node(state)
            state = await self.ats_node(state)
            decision = self.decision_node(state)
            
            if decision == "tailor":
                state = await self.tailor_node(state)
                state = await self.cover_letter_node(state)
                state = await self.apply_node(state)
                state = await self.notify_node(state)
            else:
                state = await self.skip_node(state)
            
            return state


if __name__ == "__main__":
    print("=== Job Application Agent Demo ===")
    
    initial_job = {
        "title": "Senior Python Engineer",
        "company": "TechCorp",
        "location": "San Francisco, CA",
        "url": "https://linkedin.com/jobs/mock",
        "source": "LinkedIn"
    }
    
    sample_resume = """
John Doe
Senior Software Engineer

Experience:
• Built scalable applications with Python and Django
• Worked on AWS cloud infrastructure
• Led development teams
• Delivered projects on time

Skills: Python, Django, AWS
Education: Bachelor's in Computer Science
Years of Experience: 5+ years
    """
    
    sample_applicant = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "555-1234",
        "city": "San Francisco",
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "years_experience": 5,
        "notice_period": "2 weeks",
        "current_salary": 120000,
        "expected_salary": 150000,
        "cover_letter": "",
        "portfolio_url": "https://github.com/johndoe"
    }
    
    agent = JobApplicationAgent(use_mock=True)
    
    print("\nRunning pipeline...")
    
    async def run_demo():
        result = await agent.run_pipeline(
            job=initial_job,
            resume_text=sample_resume,
            applicant=sample_applicant,
            threshold=40
        )
        
        print("\n=== Pipeline Results ===")
        print(f"ATS Score: {result['ats_score']}/100")
        print(f"Skipped: {'Yes' if result.get('skip_reason') else 'No'}")
        if result.get('skip_reason'):
            print(f"Skip Reason: {result['skip_reason']}")
        
        apply_result = result.get('apply_result', {})
        print(f"Apply Success: {apply_result.get('ok', False)}")
        print(f"Apply Message: {apply_result.get('msg', '')}")
        
        if result.get('suggestions'):
            print("\nSuggestions:")
            for i, s in enumerate(result['suggestions'], 1):
                print(f"  {i}. {s}")
    
    asyncio.run(run_demo())
    
    print("\n=== Demo Complete ===")
