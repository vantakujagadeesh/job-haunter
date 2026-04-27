import sys
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from intelligence.ats_scorer import ATSScoreEngine
except ImportError:
    from .ats_scorer import ATSScoreEngine

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class InterviewPrepGenerator:
    def __init__(self):
        self.ats_engine = ATSScoreEngine()

    def generate(
        self,
        job: Dict,
        applicant_name: str,
        openai_key: Optional[str] = None
    ) -> str:
        jd_text = job.get("desc", "")
        company = job.get("company", "the Company")
        title = job.get("title", "Position")
        
        parsed = self.ats_engine.parse_jd(jd_text)
        tech_skills = parsed.required_skills
        
        if openai_key and LLM_AVAILABLE:
            return self._generate_with_llm(job, applicant_name, openai_key)
        else:
            return self._generate_template(job, applicant_name, tech_skills)

    def _generate_with_llm(
        self,
        job: Dict,
        applicant_name: str,
        openai_key: str
    ) -> str:
        try:
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.7,
                openai_api_key=openai_key
            )
            
            prompt = f"""
You are an expert career coach. Create a comprehensive interview preparation guide for:

Name: {applicant_name}
Position: {job.get('title', 'Position')}
Company: {job.get('company', 'Company')}
Job Description:
{job.get('desc', '')}

Please structure the guide with these EXACT sections in Markdown:

## Company Research Checklist (3 bullets)
- Bullet 1
- Bullet 2
- Bullet 3

## 5 Technical Questions with Answer Hints
1. Question?
   - Hint: ...
2. Question?
   - Hint: ...
3. Question?
   - Hint: ...
4. Question?
   - Hint: ...
5. Question?
   - Hint: ...

## 5 Behavioral Questions (STAR Method)
1. Question
2. Question
3. Question
4. Question
5. Question

## 5 Smart Questions to Ask Them
1. Question
2. Question
3. Question
4. Question
5. Question

## Key Skills to Highlight
- List the key skills from the job description

## Day-Before Checklist
- 5-7 items to prepare the day before

Make it professional and actionable!
            """
            
            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            parsed = self.ats_engine.parse_jd(job.get("desc", ""))
            return self._generate_template(job, applicant_name, parsed.required_skills)

    def _generate_template(
        self,
        job: Dict,
        applicant_name: str,
        tech_skills: list
    ) -> str:
        company = job.get("company", "the Company")
        title = job.get("title", "Position")
        
        tech_questions = []
        for i, skill in enumerate(tech_skills[:5], 1):
            tech_questions.append(f"""{i}. Can you walk me through your experience with {skill}?
   - Hint: Be specific with projects, challenges, and outcomes. Use numbers where possible.""")
        
        while len(tech_questions) < 5:
            i = len(tech_questions) + 1
            tech_questions.append(f"""{i}. Describe a challenging technical problem you solved recently.
   - Hint: Focus on your thought process, debugging approach, and what you learned.""")
        
        return f"""# Interview Preparation Guide

## Applicant: {applicant_name}
## Position: {title}
## Company: {company}

---

## Company Research Checklist
- Review the company's mission, values, and recent news (last 3-6 months)
- Understand their main products/services and target market
- Research the team you'd be working with (LinkedIn, company blog)

## 5 Technical Questions with Answer Hints
{chr(10).join(tech_questions)}

## 5 Behavioral Questions (STAR Method)
1. Tell me about a time you had to meet a tight deadline.
2. Describe a situation where you had a conflict with a team member.
3. Give an example of when you took initiative on a project.
4. Tell me about a time you failed and what you learned.
5. Describe a time you adapted to a significant workplace change.

## 5 Smart Questions to Ask Them
1. What does success look like in this role in the first 90 days?
2. What are the biggest challenges the team is currently facing?
3. How would you describe the team's culture and work style?
4. What opportunities for growth and professional development are available?
5. What are the next steps in the interview process?

## Key Skills to Highlight
{chr(10).join([f"- {skill}" for skill in tech_skills[:10]])}

## Day-Before Checklist
- Review your resume and the job description one last time
- Prepare 3-5 specific stories using the STAR method
- Test your video conferencing setup (if remote)
- Plan your route or confirm virtual meeting details
- Prepare your questions for the interviewer
- Get a good night's sleep!
- Print extra copies of your resume (if in-person)

---

Good luck, {applicant_name}! You've got this! 💪
        """.strip()

    def export_pdf(self, content: str, filepath: str) -> str:
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF export")
        
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            leading=16
        )
        
        lines = content.split('\n')
        for line in lines:
            line = line.rstrip()
            
            if line.startswith('# '):
                story.append(Paragraph(line[2:], title_style))
            elif line.startswith('## '):
                story.append(Paragraph(line[3:], heading_style))
            elif line.strip() == '---':
                story.append(Spacer(1, 12))
            elif line.strip() == '':
                story.append(Spacer(1, 6))
            else:
                formatted = line.replace('**', '<b>').replace('**', '</b>')
                formatted = formatted.replace('• ', '• ')
                story.append(Paragraph(formatted, normal_style))
        
        doc.build(story)
        return filepath


if __name__ == "__main__":
    print("=== Interview Prep Generator Demo ===")
    
    sample_job = {
        "title": "Senior Python Engineer",
        "company": "TechCorp",
        "desc": """
        Requirements:
        - Python, Django, FastAPI
        - AWS, Docker, Kubernetes
        - 5+ years experience
        - REST APIs, microservices
        - Machine learning experience a plus
        """
    }
    
    generator = InterviewPrepGenerator()
    content = generator.generate(sample_job, "John Doe")
    
    print("\nGenerated Interview Prep:")
    print("=" * 60)
    print(content[:500] + "..." if len(content) > 500 else content)
    print("=" * 60)
    
    if REPORTLAB_AVAILABLE:
        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, "interview_prep.pdf")
        generator.export_pdf(content, pdf_path)
        print(f"\nPDF exported to: {pdf_path}")
    
    print("\n=== Demo Complete ===")
