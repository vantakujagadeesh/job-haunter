import os
from typing import List, Dict, Optional
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document

class ResumeRAG:
    def __init__(self, openai_key: Optional[str] = None):
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.vector_db = None
        self.embeddings = OpenAIEmbeddings(api_key=self.openai_key) if self.openai_key else None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

    def initialize_from_text(self, text: str):
        """Initializes the vector database from resume text."""
        if not self.openai_key:
            return False, "OpenAI Key missing"
        
        try:
            chunks = self.text_splitter.split_text(text)
            documents = [Document(page_content=chunk) for chunk in chunks]
            self.vector_db = FAISS.from_documents(documents, self.embeddings)
            return True, "RAG system initialized successfully"
        except Exception as e:
            return False, f"RAG initialization failed: {str(e)}"

    def get_relevant_context(self, query: str, k: int = 3) -> str:
        """Retrieves relevant resume sections for a given query (e.g., JD)."""
        if not self.vector_db:
            return ""
        
        try:
            docs = self.vector_db.similarity_search(query, k=k)
            return "\n---\n".join([doc.page_content for doc in docs])
        except Exception:
            return ""

    def tailor_resume_sections(self, jd_text: str) -> Dict[str, str]:
        """Uses RAG to find matching skills and experiences from the resume."""
        if not self.openai_key or not self.vector_db:
            return {}

        try:
            llm = ChatOpenAI(api_key=self.openai_key, model="gpt-4o-mini", temperature=0)
            
            # Find relevant parts of the resume for the JD
            context = self.get_relevant_context(jd_text, k=5)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an AI career coach. Given a Job Description and relevant sections from a candidate's resume, identify the best matching experiences and skills. Output in JSON format with keys 'matching_skills' (list) and 'relevant_experiences' (list of strings)."),
                ("human", f"Job Description:\n{jd_text}\n\nResume Context:\n{context}")
            ])
            
            chain = prompt | llm
            response = chain.invoke({})
            # Note: In a real implementation, we'd parse the JSON response
            return {"raw_response": response.content}
        except Exception:
            return {}
