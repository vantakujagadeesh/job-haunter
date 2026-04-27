# AI Job Application Agent

An advanced, autonomous agent that helps you discover jobs, evaluate them against your profile, tailor resumes/cover letters using RAG (Retrieval-Augmented Generation), and prepare for interviews.

## 🚀 Features

- **RAG Knowledge Base**: Store your entire career history in a local vector database (ChromaDB).
- **Job Scraper**: Discover jobs on LinkedIn and other boards (with demo mode support).
- **Intelligent Matching**: AI-powered "Fit Score" and rationale for every job posting.
- **Advanced Generation**: Tailor resumes and cover letters with iterative refinement and skill gap analysis.
- **Interview Coach**: Generate likely questions and STAR-method answers based on your actual experience.
- **Application Tracker**: Manage your job hunt pipeline in one place.

## 🛠️ Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

2. **Configuration**:
   - Rename `.env.example` to `.env`.
   - Add your `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

3. **Prepare Your Data**:
   - Fill out `data/career_master_template.txt` with your details.

## 🏃 Running the App

### Streamlit UI (Recommended)
```bash
streamlit run app.py
```

### CLI
```bash
python main.py --help
```

## 📂 Project Structure

- `src/rag`: RAG system and LLM management.
- `src/scraper`: Job board scraping logic.
- `src/intelligence`: Job matching and skill extraction.
- `src/interview`: Interview preparation tools.
- `src/tracking`: Application pipeline management.
- `data/`: Your resumes, career docs, and tracked applications.
