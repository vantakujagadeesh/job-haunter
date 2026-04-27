from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.outputs import LLMResult
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
from typing import Optional, List, Dict, Any
from config.settings import settings

class LLMManager:
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        temperature: float = 0.7,
        streaming: bool = False
    ):
        self.provider = provider
        self.temperature = temperature
        self.streaming = streaming

        if provider == "openai":
            self.llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=settings.openai_api_key if settings.openai_api_key else None,
                streaming=streaming,
                callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]) if streaming else None
            )
        elif provider == "anthropic":
            self.llm = ChatAnthropic(
                model=model,
                temperature=temperature,
                api_key=settings.anthropic_api_key if settings.anthropic_api_key else None,
                streaming=streaming
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_cot: bool = False,
        **kwargs
    ) -> str:
        """Enhanced generation with optional Chain of Thought."""
        if use_cot:
            prompt = f"Think step-by-step before providing your final answer.\n\n{prompt}"

        if system_prompt:
            messages = [
                ("system", system_prompt),
                ("human", prompt)
            ]
            chain = ChatPromptTemplate.from_messages(messages) | self.llm
        else:
            chain = ChatPromptTemplate.from_template("{text}") | self.llm
            messages = {"text": prompt}

        response = chain.invoke(messages)
        return response.content

    def verify_grounding(
        self,
        text: str,
        context: str
    ) -> Dict[str, Any]:
        """Verify if the generated text is supported by the provided context (Self-RAG)."""
        system_prompt = "You are a fact-checker. Verify if the claims in the generated text are supported by the provided career context."
        prompt = f"""Generated Text: {text}
        
        Career Context: {context}
        
        Are all factual claims in the 'Generated Text' supported by the 'Career Context'?
        Return a JSON with:
        - is_grounded: (boolean)
        - hallucinations: (list of claims NOT supported)
        - suggestions: (how to fix)"""
        
        import json
        response = self.generate(prompt, system_prompt)
        try:
            # Basic JSON extraction
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            return json.loads(response)
        except:
            return {"is_grounded": True, "hallucinations": [], "suggestions": []}

class ResumeTailorer:
    def __init__(self, llm_manager: Optional[LLMManager] = None):
        self.llm = llm_manager or LLMManager(temperature=0.2)

    def tailor_resume(
        self,
        resume: str,
        job_description: str,
        relevant_experience: str
    ) -> Dict[str, str]:
        """Advanced multi-pass resume tailoring."""
        
        # Pass 1: Initial Tailoring
        draft = self._generate_draft(resume, job_description, relevant_experience)
        
        # Pass 2: Self-Critique
        critique = self._critique_draft(draft, job_description)
        
        # Pass 3: Refinement based on critique
        final_resume = self._refine_with_critique(draft, critique, job_description, relevant_experience)
        
        # Pass 4: Final Analysis
        analysis = self._generate_final_analysis(final_resume, job_description)

        return {
            "tailored_resume": final_resume,
            "analysis": analysis,
            "critique": critique
        }

    def _generate_draft(self, resume, job_desc, experience):
        system_prompt = "You are an expert resume writer. Create a highly targeted resume draft."
        prompt = f"""Job Description: {job_desc}
        Candidate Experiences: {experience}
        Original Resume: {resume}
        
        Create a tailored resume draft highlighting the most relevant skills."""
        return self.llm.generate(prompt, system_prompt, use_cot=True)

    def _critique_draft(self, draft, job_desc):
        system_prompt = "You are a picky hiring manager. Critique this resume draft against the job description."
        prompt = f"""Job Description: {job_desc}
        Resume Draft: {draft}
        
        List 3 specific ways this resume could be improved to better match the job requirements."""
        return self.llm.generate(prompt, system_prompt)

    def _refine_with_critique(self, draft, critique, job_desc, experience):
        system_prompt = "You are a professional editor. Refine the resume based on the hiring manager's critique."
        prompt = f"""Original Draft: {draft}
        Critique: {critique}
        Job Description: {job_desc}
        Relevant Experience: {experience}
        
        Provide the final, polished resume."""
        return self.llm.generate(prompt, system_prompt)

    def _generate_final_analysis(self, resume, job_desc):
        system_prompt = "You are a career coach. Provide a brief analysis of the final resume."
        prompt = f"""Analyze this final resume against the job description: {job_desc}
        
        Resume: {resume}
        
        Explain why this resume is a strong match and highlight the key keywords integrated."""
        return self.llm.generate(prompt, system_prompt)

    def refine_document(
        self,
        document: str,
        feedback: str,
        context: str = ""
    ) -> str:
        system_prompt = "You are a professional editor. Refine the provided document based on the user's feedback."
        prompt = f"""Original Document:
        {document}

        User Feedback:
        {feedback}

        Additional Context:
        {context}

        Please provide the updated document."""

        return self.llm.generate(prompt, system_prompt)


class CoverLetterGenerator:
    def __init__(self, llm_manager: Optional[LLMManager] = None):
        self.llm = llm_manager or LLMManager()

    def generate(
        self,
        job_description: str,
        company_name: str,
        relevant_experience: str,
        candidate_name: str = "",
        candidate_info: str = ""
    ) -> str:
        system_prompt = """You are a professional cover letter writer. Create compelling,
        personalized cover letters that grab attention and clearly communicate why the
        candidate is an excellent fit for the position."""

        prompt = f"""Generate a professional cover letter for a job application.

        Position Details:
        {job_description}

        Company: {company_name}

        Candidate Information:
        {candidate_info}

        Most Relevant Experience from Candidate's Background:
        {relevant_experience}

        {"Candidate Name: " + candidate_name if candidate_name else ""}

        Write a compelling cover letter that:
        1. Opens with a strong hook specific to the company/role
        2. Highlights 2-3 key qualifications matching the job requirements
        3. Includes specific achievements and metrics where possible
        4. Shows genuine enthusiasm for the role and company
        5. Closes with a clear call to action

        Format as a professional business letter."""

        return self.llm.generate(prompt, system_prompt)
