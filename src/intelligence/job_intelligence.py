from typing import Dict, Any, List
from src.rag.llm_manager import LLMManager
from src.rag.knowledge_base import KnowledgeBase
import json
import logging

logger = logging.getLogger(__name__)

class JobIntelligence:
    def __init__(self, llm_manager: LLMManager = None):
        self.llm = llm_manager or LLMManager(temperature=0.3) # Lower temperature for more objective analysis

    def evaluate_match(
        self,
        job_description: str,
        career_history: str
    ) -> Dict[str, Any]:
        """Evaluate how well a job matches the candidate's history."""
        system_prompt = """You are a senior technical recruiter. Your task is to evaluate
        a job description against a candidate's career history. You must provide a match
        score and a detailed rationale in JSON format."""

        prompt = f"""Job Description:
        {job_description}

        Candidate Career History:
        {career_history}

        Analyze the match based on:
        1. Skills overlap (technical and soft skills)
        2. Experience level (years and seniority)
        3. Industry relevance
        4. Potential growth vs current profile

        Return ONLY a JSON object with the following keys:
        - match_score: (integer between 0 and 100)
        - strengths: (list of matching skills/experiences)
        - gaps: (list of missing skills or experience)
        - rationale: (brief summary of the fit)
        """

        response = self.llm.generate(prompt, system_prompt)

        try:
            # Attempt to extract JSON from the response if it's wrapped in markdown
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Error parsing match evaluation: {e}")
            return {
                "match_score": 0,
                "strengths": [],
                "gaps": [],
                "rationale": "Failed to generate evaluation."
            }

    def extract_skills(self, text: str) -> List[str]:
        """Extract a list of skills from a job description or resume."""
        system_prompt = "You are a specialized NLP tool that extracts technical and soft skills from text."
        prompt = f"Extract all relevant professional skills from the following text and return them as a comma-separated list:\n\n{text}"

        response = self.llm.generate(prompt, system_prompt)
        return [s.strip() for s in response.split(",")]
