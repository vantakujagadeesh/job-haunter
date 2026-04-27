import asyncio
import sys
import logging
from typing import TypedDict, Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict

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

logger = logging.getLogger(__name__)

@dataclass
class AgentState:
    job: Dict[str, Any] = field(default_factory=dict)
    resume_text: str = ""
    applicant: Dict[str, Any] = field(default_factory=dict)
    credentials: Dict[str, str] = field(default_factory=dict)
    resume_path: str = ""
    ats_score: int = 0
    ats_breakdown: Dict[str, Any] = field(default_factory=dict)
    tailored_resume: str = ""
    cover_letter: str = ""
    apply_result: Dict[str, Any] = field(default_factory=lambda: {"ok": False, "msg": "Pipeline not executed", "ts": None})
    email_sent: bool = False
    skip_reason: str = ""
    threshold: int = 60
    suggestions: List[str] = field(default_factory=list)
    openai_key: Optional[str] = None
    rag_engine: Any = None
    status: str = "initialized"
    errors: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    runtime_meta: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def update_timestamp(self) -> None:
        self.updated_at = datetime.now().isoformat()

    def record(self, message: str) -> None:
        self.update_timestamp()
        self.history.append(f"[{self.updated_at}] {message}")

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.status = "error"
        self.record(f"ERROR: {message}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AgentState":
        state = AgentState()
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state


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

    async def _safe_execute(self, node_name: str, node_fn, state: AgentState) -> AgentState:
        state.record(f"Entering {node_name}")
        try:
            result = await node_fn(state)
            result.record(f"Completed {node_name}")
            return result
        except Exception as exc:
            message = f"{node_name} failed: {str(exc)}"
            logger.exception(message)
            state.add_error(message)
            if node_name == "apply":
                state.apply_result = {"ok": False, "msg": message, "ts": datetime.now().isoformat()}
            return state

    def _create_state(
        self,
        job: Dict[str, Any],
        resume_text: str,
        applicant: Dict[str, Any],
        credentials: Dict[str, str] = None,
        resume_path: str = "",
        threshold: int = 60,
        openai_key: Optional[str] = None,
        rag_engine: Any = None
    ) -> AgentState:
        state = AgentState(
            job=job or {},
            resume_text=resume_text or "",
            applicant=applicant or {},
            credentials=credentials or {},
            resume_path=resume_path,
            threshold=threshold,
            openai_key=openai_key,
            rag_engine=rag_engine
        )
        state.record("Pipeline initialized")
        return state

    async def research_node(self, state: AgentState) -> AgentState:
        state.status = "research"
        job = state.job or {}
        url = job.get("url", "")
        source = job.get("source", "LinkedIn")

        if url and not self.use_mock and source == "LinkedIn":
            try:
                await self.linkedin_scraper.start()
                description = await self.linkedin_scraper.get_job_description(url)
                await self.linkedin_scraper.stop()
                if description:
                    job["desc"] = description
                else:
                    state.record("LinkedIn returned no description")
            except Exception as exc:
                state.add_error(f"LinkedIn research failed: {exc}")
        else:
            if self.use_mock:
                state.record("Mock research mode: skipping live job fetch")

        if not job.get("desc"):
            job["desc"] = self._get_default_jd()
            state.record("Using default job description fallback")

        state.job = job
        return state

    async def ats_node(self, state: AgentState) -> AgentState:
        state.status = "ats_scoring"
        resume_text = state.resume_text
        jd_text = state.job.get("desc", "")

        if not resume_text:
            state.add_error("No resume text available for ATS scoring.")
            return state

        if not jd_text:
            state.add_error("No job description available for ATS scoring.")
            return state

        self.ats_engine.load_resume(resume_text)
        score, breakdown = self.ats_engine.calculate_score(jd_text)
        suggestions = self.ats_engine.suggest_improvements(score, breakdown)

        state.ats_score = score
        state.ats_breakdown = breakdown
        state.suggestions = suggestions
        state.runtime_meta["ats_evaluated_at"] = datetime.now().isoformat()
        return state

    def decision_node(self, state: AgentState) -> str:
        state.record("Running decision node")
        if state.ats_score >= state.threshold:
            return "tailor"

        if state.ats_score == 0 and state.resume_text and state.job.get("desc"):
            state.record("ATS score 0, allowing tailoring attempt for possible low-signal resume")
            return "tailor"

        state.skip_reason = f"ATS score {state.ats_score} below threshold {state.threshold}."
        state.runtime_meta["decision_reason"] = state.skip_reason
        return "skip"

    async def tailor_node(self, state: AgentState) -> AgentState:
        state.status = "tailoring"
        resume_text = state.resume_text
        jd_text = state.job.get("desc", "")
        if not resume_text or not jd_text:
            state.add_error("Tailoring skipped because resume text or job description is missing.")
            return state

        context = ""
        if state.rag_engine:
            try:
                context = state.rag_engine.get_relevant_context(jd_text, k=5)
                state.runtime_meta["rag_context_length"] = len(context)
            except Exception as exc:
                state.record(f"RAG context retrieval failed: {exc}")

        tailored_resume = resume_text
        if state.openai_key:
            try:
                from src.rag.llm_manager import ResumeTailorer, LLMManager
                tailor = ResumeTailorer(LLMManager(provider="openai", temperature=0.2))
                tailored_payload = tailor.tailor_resume(resume_text, jd_text, context)
                tailored_resume = tailored_payload.get("tailored_resume", resume_text)
                state.runtime_meta["tailor_mode"] = "llm"
            except Exception as exc:
                state.record(f"LLM resume tailoring failed: {exc}")
                tailored_resume = self._legacy_tailor(resume_text, jd_text)
                state.runtime_meta["tailor_mode"] = "fallback"
        else:
            tailored_resume = self._legacy_tailor(resume_text, jd_text)
            state.runtime_meta["tailor_mode"] = "legacy"

        state.tailored_resume = tailored_resume
        return state

    async def cover_letter_node(self, state: AgentState) -> AgentState:
        state.status = "cover_letter"
        applicant = state.applicant or {}
        job = state.job or {}
        tailored_resume = state.tailored_resume or state.resume_text
        name = applicant.get("name", "Applicant")
        company = job.get("company", "Company")
        title = job.get("title", "Position")
        jd = job.get("desc", "")

        context = ""
        if state.rag_engine and jd:
            try:
                context = state.rag_engine.get_relevant_context(jd, k=3)
            except Exception as exc:
                state.record(f"Cover letter RAG context failed: {exc}")

        cl_agent = CoverLetterAgent(state.openai_key)
        input_text = f"Resume:\n{tailored_resume[:1200]}\n\nRelevant Resume Context:\n{context}"
        cover_letter = cl_agent.generate(name, company, title, jd, input_text)

        state.cover_letter = cover_letter
        return state

    async def apply_node(self, state: AgentState) -> AgentState:
        state.status = "apply"
        job = state.job or {}
        applicant = state.applicant or {}
        resume_path = state.resume_path
        source = job.get("source", "LinkedIn")

        apply_result = {"ok": False, "msg": "No application attempted", "ts": datetime.now().isoformat()}

        if self.use_mock:
            await asyncio.sleep(1)
            apply_result = {"ok": True, "msg": "Mock application submitted", "ts": datetime.now().isoformat()}
        else:
            try:
                if source == "LinkedIn":
                    await self.linkedin_scraper.start()
                    success, msg = await self.linkedin_scraper.easy_apply(job, applicant, resume_path)
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
                else:
                    apply_result = {"ok": False, "msg": f"Unsupported source: {source}", "ts": datetime.now().isoformat()}
            except Exception as exc:
                message = f"Application step failed: {exc}"
                logger.exception(message)
                apply_result = {"ok": False, "msg": message, "ts": datetime.now().isoformat()}

        state.apply_result = apply_result
        return state

    async def notify_node(self, state: AgentState) -> AgentState:
        state.status = "notify"
        state.email_sent = True
        state.record("Notification step completed")
        return state

    async def skip_node(self, state: AgentState) -> AgentState:
        state.status = "skipped"
        state.record(f"Pipeline skipped: {state.skip_reason}")
        state.apply_result = {"ok": False, "msg": state.skip_reason or "Skipped by pipeline decision", "ts": datetime.now().isoformat()}
        return state

    def _legacy_tailor(self, resume_text: str, jd_text: str) -> str:
        bullets = self._extract_bullets(resume_text)
        if bullets:
            rewritten = self.ats_engine.rewrite_bullets(bullets, jd_text, self.ats_engine.embedding_model and None)
            return self._replace_bullets(resume_text, bullets, rewritten)

        parsed = self.ats_engine.parse_jd(jd_text)
        keywords = parsed.required_skills + parsed.nice_to_have
        missing_keywords = [k for k in keywords if k.lower() not in resume_text.lower()]
        if missing_keywords and "Skills:" in resume_text:
            return resume_text.replace("Skills:", f"Skills: {', '.join(missing_keywords[:5])}, ")
        return resume_text

    def _extract_bullets(self, text: str) -> List[str]:
        bullets = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("•") or stripped.startswith("-"):
                bullets.append(stripped.lstrip("•- ").strip())
        return bullets

    def _replace_bullets(self, text: str, original: List[str], rewritten: List[str]) -> str:
        lines = text.splitlines()
        new_lines: List[str] = []
        bullet_idx = 0
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith("•") or stripped.startswith("-")) and bullet_idx < len(rewritten):
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{indent}• {rewritten[bullet_idx]}")
                bullet_idx += 1
            else:
                new_lines.append(line)
        return "\n".join(new_lines)

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
        return None

    async def run_pipeline(
        self,
        job: Dict[str, Any],
        resume_text: str,
        applicant: Dict[str, Any],
        credentials: Dict[str, str] = None,
        resume_path: str = "",
        threshold: int = 60,
        openai_key: Optional[str] = None,
        rag_engine: Any = None
    ) -> Dict[str, Any]:
        state = self._create_state(
            job=job,
            resume_text=resume_text,
            applicant=applicant,
            credentials=credentials,
            resume_path=resume_path,
            threshold=threshold,
            openai_key=openai_key,
            rag_engine=rag_engine
        )

        state = await self._safe_execute("research", self.research_node, state)
        if state.status == "error":
            return state.to_dict()

        state = await self._safe_execute("ats", self.ats_node, state)
        if state.status == "error":
            return state.to_dict()

        decision = self.decision_node(state)
        state.runtime_meta["decision"] = decision

        if decision == "tailor":
            state = await self._safe_execute("tailor", self.tailor_node, state)
            if state.status == "error":
                return state.to_dict()

            state = await self._safe_execute("cover_letter", self.cover_letter_node, state)
            if state.status == "error":
                return state.to_dict()

            state = await self._safe_execute("apply", self.apply_node, state)
            if state.status == "error":
                return state.to_dict()

            state = await self._safe_execute("notify", self.notify_node, state)
            state.status = "completed" if state.apply_result.get("ok") else "failed"
        else:
            state = await self._safe_execute("skip", self.skip_node, state)
            state.status = "skipped"

        return state.to_dict()


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
        print(f"Status: {result.get('status')}")
        print(f"ATS Score: {result.get('ats_score')}/100")
        print(f"Skipped: {'Yes' if result.get('skip_reason') else 'No'}")
        if result.get('skip_reason'):
            print(f"Skip Reason: {result.get('skip_reason')}")

        apply_result = result.get('apply_result', {})
        print(f"Apply Success: {apply_result.get('ok', False)}")
        print(f"Apply Message: {apply_result.get('msg', '')}")

        if result.get('errors'):
            print("\nErrors:")
            for err in result.get('errors', []):
                print(f" - {err}")

        if result.get('suggestions'):
            print("\nSuggestions:")
            for i, s in enumerate(result.get('suggestions', []), 1):
                print(f"  {i}. {s}")

    asyncio.run(run_demo())
    print("\n=== Demo Complete ===")
