from typing import List, Optional
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from config.settings import settings
import os

class KnowledgeBase:
    def __init__(
        self,
        collection_name: str = "career_knowledge",
        embedding_model: Optional[str] = None,
        embedding_dimensions: int = 1536
    ):
        self.collection_name = collection_name
        self.embedding = OpenAIEmbeddings(
            model=embedding_model or settings.embedding_model,
            api_key=settings.openai_api_key if settings.openai_api_key else None
        )
        self.vectorstore = Chroma(
            collection_name=collection_name,
            persist_directory=str(settings.chroma_persist_directory),
            embedding_function=self.embedding
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
        )

    def load_resumes(self, directory: str = None) -> List[Document]:
        load_dir = directory or str(settings.resumes_directory)
        if not os.path.exists(load_dir):
            os.makedirs(load_dir, exist_ok=True)
            return []

        all_docs = []
        
        # Load Text Resumes
        txt_loader = DirectoryLoader(
            load_dir,
            glob="**/*.txt",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        all_docs.extend(txt_loader.load())
        
        # Load PDF Resumes
        pdf_loader = DirectoryLoader(
            load_dir,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader
        )
        all_docs.extend(pdf_loader.load())
        
        return all_docs

    def load_career_master_document(self, file_path: str) -> List[Document]:
        loader = TextLoader(file_path, encoding="utf-8")
        return loader.load()

    def add_documents(self, documents: List[Document], metadata: dict = None):
        if not documents:
            return

        chunks = self.text_splitter.split_documents(documents)
        for chunk in chunks:
            if metadata:
                chunk.metadata.update(metadata)

        self.vectorstore.add_documents(chunks)

    def ingest_resumes(self):
        documents = self.load_resumes()
        if documents:
            self.add_documents(documents, {"source": "resume"})
            return len(documents)
        return 0

    def query(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict = None,
        multi_query: bool = False,
        llm_manager: Optional[any] = None
    ) -> List[Document]:
        """Query the vectorstore with optional multi-query expansion."""
        if not multi_query:
            return self.vectorstore.similarity_search(
                query,
                k=k,
                filter=filter_metadata
            )
        
        if not llm_manager:
            from .llm_manager import LLMManager
            llm_manager = LLMManager(temperature=0.1)

        # Multi-query expansion
        system_prompt = "You are a helpful assistant that generates multiple search queries based on a single input query."
        prompt = f"""Generate 3 different versions of the following search query to improve retrieval from a vector database.
        The goal is to find relevant career experiences.
        Original Query: {query}
        Return only the queries, one per line."""
        
        expanded_queries_text = llm_manager.generate(prompt, system_prompt)
        queries = [q.strip() for q in expanded_queries_text.split("\n") if q.strip()]
        queries.append(query) # Include original

        all_results = []
        for q in queries:
            results = self.vectorstore.similarity_search(q, k=k, filter=filter_metadata)
            all_results.extend(results)
        
        # Deduplicate by content
        seen = set()
        unique_results = []
        for doc in all_results:
            if doc.page_content not in seen:
                unique_results.append(doc)
                seen.add(doc.page_content)
        
        return unique_results[:k*2] # Return more candidates for reranking

    def get_relevant_experience(
        self,
        job_description: str,
        k: int = 5,
        multi_query: bool = True,
        llm_manager: Optional[any] = None
    ) -> str:
        """Get relevant experiences using advanced retrieval."""
        results = self.query(
            job_description, 
            k=k, 
            multi_query=multi_query, 
            llm_manager=llm_manager
        )
        
        # If we have a lot of results, we can rerank them
        if len(results) > k and llm_manager:
            results = self.rerank_results(job_description, results, k, llm_manager)

        return "\n\n".join([f"--- EXPERIENCE START ---\n{doc.page_content}\n--- EXPERIENCE END ---" for doc in results])

    def rerank_results(
        self,
        query: str,
        documents: List[Document],
        k: int,
        llm_manager: any
    ) -> List[Document]:
        """Rerank documents using an LLM to find the absolute best matches."""
        system_prompt = "You are an expert recruiter. Your task is to rank the relevance of candidate experiences to a job description."
        
        doc_texts = "\n".join([f"[{i}] {doc.page_content[:300]}..." for i, doc in enumerate(documents)])
        
        prompt = f"""Job Description: {query}
        
        Candidate Experiences:
        {doc_texts}
        
        Rank the experiences from most relevant to least relevant to the job description.
        Return ONLY the indices in order, like: 2, 0, 1.
        Return at most {k} indices."""
        
        try:
            ranking_text = llm_manager.generate(prompt, system_prompt)
            indices = [int(i.strip()) for i in ranking_text.split(",") if i.strip().isdigit()]
            
            reranked = []
            for idx in indices:
                if 0 <= idx < len(documents):
                    reranked.append(documents[idx])
            
            return reranked[:k]
        except Exception:
            return documents[:k] # Fallback to original order

    def delete_collection(self):
        self.vectorstore.delete_collection()

    def get_collection_info(self) -> dict:
        return {
            "name": self.collection_name,
            "count": self.vectorstore._collection.count(),
            "persist_directory": str(settings.chroma_persist_directory)
        }


def create_knowledge_base(collection_name: str = "career_knowledge") -> KnowledgeBase:
    return KnowledgeBase(collection_name=collection_name)
