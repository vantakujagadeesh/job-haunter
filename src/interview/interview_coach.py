from typing import List, Dict, Any
from src.rag.llm_manager import LLMManager
from src.rag.knowledge_base import KnowledgeBase
import logging

logger = logging.getLogger(__name__)

class InterviewCoach:
    def __init__(self, llm_manager: LLMManager = None):
        self.llm = llm_manager or LLMManager(temperature=0.8) # Higher temperature for more creative interview preparation

    def generate_interview_questions(
        self,
        job_description: str,
        career_history: str,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """Generate likely interview questions based on job description and candidate history."""
        system_prompt = """You are an expert interviewer. Your task is to generate challenging
        but fair interview questions for a specific job and candidate profile."""

        prompt = f"""Job Description:
        {job_description}

        Candidate Career History:
        {career_history}

        Generate {limit} interview questions. For each question, provide a brief 'Rationale'
        explaining why this question is likely to be asked based on the job requirements.

        Format as:
        Q1: [Question]
        Rationale: [Why it's asked]
        ---
        Q2: [Question]
        Rationale: [Why it's asked]
        ..."""

        response = self.llm.generate(prompt, system_prompt)

        # Basic parsing
        questions = []
        parts = response.split("---")
        for part in parts:
            lines = part.strip().split("\n")
            if len(lines) >= 2:
                q_text = lines[0].replace("Q" + str(len(questions)+1) + ":", "").strip()
                r_text = lines[1].replace("Rationale:", "").strip()
                questions.append({"question": q_text, "rationale": r_text})

        return questions

    def answer_question_with_rag(
        self,
        question: str,
        job_description: str,
        relevant_experience: str
    ) -> str:
        """Answer an interview question using the candidate's actual experience from RAG."""
        system_prompt = """You are an interview coach helping a candidate prepare.
        Use their actual experiences to construct a compelling answer using the STAR method
        (Situation, Task, Action, Result)."""

        prompt = f"""Question: {question}

        Job Context: {job_description}

        Candidate's Relevant Experience (from RAG):
        {relevant_experience}

        Construct a high-quality interview answer using the STAR method.
        Ensure it:
        1. Directly addresses the question.
        2. Highlights specific technologies and metrics from the candidate's history.
        3. Shows how the candidate's experience solves the problems in the job description.
        """

        return self.llm.generate(prompt, system_prompt)
