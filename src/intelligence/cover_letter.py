"""
Cover Letter Generator Agent
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class CoverLetterAgent:
    def __init__(self, openai_key: Optional[str] = None):
        self.api_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.llm = None
        
        if self.api_key and LLM_AVAILABLE:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    temperature=0.7,
                    openai_api_key=self.api_key
                )
            except Exception:
                pass

    def generate(
        self,
        user_name: str,
        company: str,
        job_title: str,
        job_description: str,
        resume_summary: str = ""
    ) -> str:
        """Generate a personalized cover letter."""
        prompt = f"""
        Write a professional, concise cover letter (max 1 page) for:
        Name: {user_name}
        Position: {job_title}
        Company: {company}
        
        Job Description:
        {job_description}
        
        My Background (resume summary):
        {resume_summary or "I am a passionate software engineer with experience in building scalable applications."}
        
        Requirements:
        - Start with a strong opening
        - Tailor 1-2 paragraphs specifically to {company}
        - End with a call to action
        - Be professional and concise
        """
        
        # Use LLM if available, otherwise a high-quality template
        if self.llm:
            try:
                response = self.llm.invoke(prompt)
                return response.content
            except Exception:
                pass
                
        # Fallback: High-quality template
        return self._generate_template(user_name, company, job_title, job_description)

    def _generate_template(
        self, user_name: str, company: str, job_title: str, jd: str
    ) -> str:
        """Professional fallback cover letter template."""
        return f"""
{user_name}
[Your Address]
[City, State]
[Email]
[Phone]
[Date]

Hiring Manager
{company}
[Company Address]

Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company}.

After reading the job description, I was particularly excited about the opportunity to bring my skills in {self._extract_key_skills(jd)} to your team. Throughout my career, I have consistently demonstrated my ability to build scalable solutions and contribute to high-performing teams.

What excites me most about {company} is your commitment to innovation and impact. I admire how your company pushes boundaries in the industry, and I am eager to contribute to that mission.

Thank you for considering my application. I would welcome the chance to discuss how my background and enthusiasm can benefit {company}.

Sincerely,
{user_name}
        """.strip()

    def _extract_key_skills(self, jd: str) -> str:
        """Extract a few key skills from JD for the template."""
        jd_lower = jd.lower()
        skills = []
        common_skills = ["Python", "Java", "JavaScript", "AWS", "Docker", "React", "SQL"]
        for skill in common_skills:
            if skill.lower() in jd_lower:
                skills.append(skill)
        return ", ".join(skills[:3]) if skills else "software development"
