"""
ATS Score Engine - Intelligence Upgrade
"""
import re
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

try:
    import spacy
    from spacy.tokens import Doc
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class ParsedJD:
    job_title: str = ""
    required_skills: List[str] = None
    nice_to_have: List[str] = None
    years_exp: int = 0
    education_level: str = ""
    
    def __post_init__(self):
        if self.required_skills is None:
            self.required_skills = []
        if self.nice_to_have is None:
            self.nice_to_have = []


class ATSScoreEngine:
    def __init__(self, resume_text: str = ""):
        self.resume_text = resume_text
        self.resume_text_lower = ""
        
        self.nlp = None
        self.embedding_model = None
        
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except:
                pass
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except:
                pass
        
        self._tech_skills = [
            "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
            "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "matplotlib",
            "aws", "azure", "gcp", "kubernetes", "docker", "terraform", "ansible",
            "react", "angular", "vue", "next.js", "flask", "django", "fastapi",
            "sql", "nosql", "mongodb", "postgresql", "mysql", "redis", "elasticsearch",
            "git", "ci/cd", "jenkins", "github actions", "agile", "scrum",
            "machine learning", "deep learning", "nlp", "computer vision", "data science",
            "api", "rest", "graphql", "microservices", "oop", "design patterns",
            "linux", "unix", "bash", "shell", "windows", "macos"
        ]
        
        self._education_levels = [
            ("phd", "PhD"),
            ("doctorate", "PhD"),
            ("master", "Master's"),
            ("ms", "Master's"),
            ("m.s", "Master's"),
            ("mba", "MBA"),
            ("bachelor", "Bachelor's"),
            ("bs", "Bachelor's"),
            ("b.s", "Bachelor's"),
            ("ba", "Bachelor's"),
            ("b.a", "Bachelor's"),
            ("associate", "Associate's"),
            ("high school", "High School"),
            ("hs", "High School")
        ]

    def load_resume(self, resume_text: str):
        self.resume_text = resume_text
        self.resume_text_lower = resume_text.lower()

    def parse_jd(self, text: str) -> ParsedJD:
        parsed = ParsedJD()
        text_lower = text.lower()
        
        job_title_match = re.search(r'(?i)(job title|position|role):?\s*([^\n]+)', text)
        if job_title_match:
            parsed.job_title = job_title_match.group(2).strip()
        else:
            lines = text.split('\n')
            for line in lines[:10]:
                if len(line.strip()) > 0 and len(line.strip()) < 100:
                    parsed.job_title = line.strip()
                    break
        
        yoe_match = re.search(r'(\d+)\+?\s*(years?|yr)\s*(of\s*)?experience', text_lower)
        if yoe_match:
            parsed.years_exp = int(yoe_match.group(1))
        else:
            yoe_match2 = re.search(r'(\d+)\s*-\s*(\d+)\s*(years?|yr)', text_lower)
            if yoe_match2:
                parsed.years_exp = (int(yoe_match2.group(1)) + int(yoe_match2.group(2))) // 2
        
        for keyword, level in self._education_levels:
            if keyword in text_lower:
                parsed.education_level = level
                break
        
        found_skills = []
        for skill in self._tech_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        nice_to_have_keywords = ["nice to have", "bonus", "plus", "preferred", "desirable"]
        has_nice_to_have_section = any(k in text_lower for k in nice_to_have_keywords)
        
        if has_nice_to_have_section:
            sections = re.split(r'(?i)(nice to have|bonus|plus|preferred|desirable)', text, flags=re.IGNORECASE)
            if len(sections) > 1:
                nice_section = sections[-1].lower()
                for skill in found_skills:
                    if skill in nice_section:
                        parsed.nice_to_have.append(skill)
                parsed.required_skills = [s for s in found_skills if s not in parsed.nice_to_have]
            else:
                parsed.required_skills = found_skills[:max(1, len(found_skills)*2//3)]
                parsed.nice_to_have = found_skills[len(parsed.required_skills):]
        else:
            parsed.required_skills = found_skills
        
        return parsed

    def _calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        if not self.embedding_model or not SENTENCE_TRANSFORMERS_AVAILABLE:
            return 0.0
        
        try:
            embeddings = self.embedding_model.encode([text1, text2])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except:
            return 0.0

    def _calculate_keyword_overlap(self, jd_keywords: List[str], resume_text: str) -> Tuple[float, List[str], List[str]]:
        resume_lower = resume_text.lower()
        matched = []
        missing = []
        
        for keyword in jd_keywords:
            if keyword.lower() in resume_lower:
                matched.append(keyword)
            else:
                missing.append(keyword)
        
        overlap_score = len(matched) / len(jd_keywords) if jd_keywords else 0.0
        return overlap_score, matched, missing

    def calculate_score(self, jd_text: str) -> Tuple[int, Dict]:
        if not self.resume_text:
            return 0, {"error": "No resume loaded"}

        parsed_jd = self.parse_jd(jd_text)
        score_breakdown = {}
        total_score = 0
        
        all_keywords = parsed_jd.required_skills + parsed_jd.nice_to_have
        
        keyword_score = 0
        if self.embedding_model and SENTENCE_TRANSFORMERS_AVAILABLE:
            cosine_sim = self._calculate_cosine_similarity(self.resume_text, jd_text)
            keyword_score = int(cosine_sim * 60)
        else:
            overlap, matched, missing = self._calculate_keyword_overlap(all_keywords, self.resume_text)
            keyword_score = int(overlap * 60)
        
        score_breakdown["Keyword Match (60%)"] = keyword_score
        score_breakdown["Required Skills"] = parsed_jd.required_skills
        score_breakdown["Nice to Have Skills"] = parsed_jd.nice_to_have
        total_score += keyword_score
        
        exp_score = 0
        if parsed_jd.years_exp > 0:
            resume_yoe_match = re.search(r'(\d+)\+?\s*(years?|yr)\s*(of\s*)?experience', self.resume_text_lower)
            resume_yoe = int(resume_yoe_match.group(1)) if resume_yoe_match else 0
            
            if resume_yoe >= parsed_jd.years_exp:
                exp_score = 20
            else:
                ratio = resume_yoe / parsed_jd.years_exp
                exp_score = int(ratio * 20)
        else:
            exp_score = 15
        
        score_breakdown["Experience Match (20%)"] = exp_score
        score_breakdown["Required Years"] = parsed_jd.years_exp
        total_score += exp_score
        
        edu_score = 0
        format_score = 0
        
        if parsed_jd.education_level:
            has_edu = any(ed in self.resume_text_lower for ed, _ in self._education_levels)
            edu_score = 10 if has_edu else 5
        else:
            edu_score = 10
        
        word_count = len(self.resume_text.split())
        if 300 < word_count < 1200:
            format_score += 5
        elif 200 < word_count:
            format_score += 3
        
        bullet_points = self.resume_text.count("•") + self.resume_text.count("- ")
        if bullet_points > 5:
            format_score += 5
        elif bullet_points > 2:
            format_score += 3
        
        score_breakdown["Education & Format (20%)"] = edu_score + format_score
        total_score += edu_score + format_score
        
        final_score = min(100, max(0, total_score))
        
        return final_score, score_breakdown

    def suggest_improvements(self, score: int, breakdown: Dict) -> List[str]:
        suggestions = []
        
        required = breakdown.get("Required Skills", [])
        if required:
            missing = [s for s in required if s.lower() not in self.resume_text_lower]
            if missing:
                suggestions.append(f"Add missing required skills: {', '.join(missing[:5])}")
        
        nice_to_have = breakdown.get("Nice to Have Skills", [])
        if nice_to_have:
            missing_nice = [s for s in nice_to_have if s.lower() not in self.resume_text_lower]
            if missing_nice:
                suggestions.append(f"Consider adding nice-to-have skills: {', '.join(missing_nice[:3])}")
        
        if breakdown.get("Experience Match (20%)", 0) < 15:
            suggestions.append("Highlight your relevant experience more prominently.")
        
        if breakdown.get("Education & Format (20%)", 0) < 15:
            suggestions.append("Improve formatting: Use bullet points and keep it 1-2 pages.")
        
        if score < 60:
            suggestions.append("Consider a more significant rewrite to match the job description.")
        elif score < 80:
            suggestions.append("A few tweaks should significantly improve your ATS score.")
        
        return suggestions

    def rewrite_bullets(self, bullets: List[str], jd_text: str, openai_key: Optional[str] = None) -> List[str]:
        if openai_key and OPENAI_AVAILABLE:
            try:
                llm = ChatOpenAI(api_key=openai_key, model="gpt-4o-mini", temperature=0.5)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are an elite executive resume writer. Your task is to rewrite resume bullet points to maximize ATS compatibility and human impact. "
                               "Rules:\n1. Use powerful action verbs.\n2. Quantify achievements with metrics where possible.\n3. Mirror the specific terminology and keywords found in the Job Description.\n"
                               "4. Maintain absolute truthfulness—do not invent experiences.\n5. Keep each bullet concise (under 25 words)."),
                    ("human", "Job Description:\n{jd}\n\nOriginal Bullet Points:\n{bullets}\n\nPlease provide a tailored list of bullets, one per line.")
                ])
                chain = prompt | llm
                response = chain.invoke({"jd": jd_text, "bullets": "\n".join(bullets)})
                rewritten = [b.strip().lstrip("•- ") for b in response.content.split("\n") if b.strip()]
                return rewritten if len(rewritten) == len(bullets) else rewritten[:len(bullets)]
            except Exception as e:
                print(f"LLM Rewriting failed: {e}")
                pass
        
        parsed_jd = self.parse_jd(jd_text)
        all_keywords = parsed_jd.required_skills + parsed_jd.nice_to_have
        missing_keywords = [k for k in all_keywords if k.lower() not in self.resume_text_lower]
        
        rewritten = []
        keywords_to_add = missing_keywords[:3]
        
        for bullet in bullets:
            new_bullet = bullet
            if keywords_to_add:
                keyword_str = ", ".join(keywords_to_add)
                if " and " not in new_bullet.lower() and len(new_bullet) < 200:
                    new_bullet = f"{new_bullet.rstrip('.')}, utilizing {keyword_str}."
            rewritten.append(new_bullet)
        
        return rewritten


if __name__ == "__main__":
    print("=== ATS Score Engine Demo ===")
    
    sample_resume = """
    John Doe
    Senior Software Engineer
    
    Experience:
    • Developed scalable web applications using Python and Django
    • Implemented machine learning models with TensorFlow and scikit-learn
    • Managed cloud infrastructure on AWS with Docker and Kubernetes
    • Led a team of 5 engineers and delivered projects on time
    
    Skills: Python, Django, AWS, Docker, Kubernetes, TensorFlow, SQL
    Education: Bachelor's in Computer Science
    Years of Experience: 5+ years
    """
    
    sample_jd = """
    Job Title: Senior Full Stack Engineer
    
    We are looking for an experienced engineer with:
    - 4+ years of experience
    - Python, Django, FastAPI
    - AWS, Docker, Kubernetes
    - React, JavaScript
    - Machine learning experience with TensorFlow or PyTorch is a plus
    - Bachelor's degree in Computer Science or related field
    
    Nice to have:
    - GraphQL experience
    - CI/CD with GitHub Actions
    """
    
    print("\nLoading resume...")
    ats = ATSScoreEngine()
    ats.load_resume(sample_resume)
    
    print("\nParsing job description...")
    parsed = ats.parse_jd(sample_jd)
    print(f"  Job Title: {parsed.job_title}")
    print(f"  Required Skills: {', '.join(parsed.required_skills)}")
    print(f"  Nice to Have: {', '.join(parsed.nice_to_have)}")
    print(f"  Years Required: {parsed.years_exp}")
    print(f"  Education: {parsed.education_level}")
    
    print("\nCalculating score...")
    score, breakdown = ats.calculate_score(sample_jd)
    print(f"  ATS Score: {score}/100")
    print(f"\n  Breakdown:")
    for key, value in breakdown.items():
        if isinstance(value, (int, float)):
            print(f"    {key}: {value}")
    
    print("\nSuggestions:")
    suggestions = ats.suggest_improvements(score, breakdown)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"  {i}. {suggestion}")
    
    print("\nRewriting bullet points (no OpenAI key)...")
    sample_bullets = [
        "Developed web applications",
        "Worked on cloud infrastructure",
        "Led team projects"
    ]
    rewritten = ats.rewrite_bullets(sample_bullets, sample_jd)
    print("\n  Original:")
    for b in sample_bullets:
        print(f"    - {b}")
    print("\n  Rewritten:")
    for b in rewritten:
        print(f"    - {b}")
    
    print("\n=== Demo Complete ===")
