#!/usr/bin/env python3
"""
Job Application Agent - Main Entry Point
Phase 1: Knowledge Base & RAG System
"""

import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.rag import KnowledgeBase, create_knowledge_base, ResumeTailorer, CoverLetterGenerator
from src.scraper import ScraperOrchestrator
import asyncio


def setup_directories():
    settings.resumes_directory.mkdir(parents=True, exist_ok=True)
    settings.jobs_directory.mkdir(parents=True, exist_ok=True)
    settings.chroma_persist_directory.mkdir(parents=True, exist_ok=True)


def initialize_knowledge_base():
    kb = create_knowledge_base()
    setup_directories()
    return kb


def cmd_ingest(kb: KnowledgeBase, career_file: str = None):
    print("🚀 Starting data ingestion...")

    count = kb.ingest_resumes()
    print(f"✅ Ingested {count} resume(s)")

    if career_file and os.path.exists(career_file):
        from langchain_community.document_loaders import TextLoader
        docs = TextLoader(career_file, encoding="utf-8").load()
        kb.add_documents(docs, {"source": "career_master"})
        print(f"✅ Ingested career master document: {career_file}")

    info = kb.get_collection_info()
    print(f"\n📊 Knowledge Base Info:")
    print(f"   Collection: {info['name']}")
    print(f"   Documents: {info['count']}")
    print(f"   Location: {info['persist_directory']}")


def cmd_query(kb: KnowledgeBase, query: str, k: int = 5):
    print(f"🔍 Querying: {query}\n")
    results = kb.query(query, k=k)

    for i, doc in enumerate(results, 1):
        print(f"--- Result {i} ---")
        print(doc.page_content[:500])
        if len(doc.page_content) > 500:
            print("...")
        print()


def cmd_tailor(kb: KnowledgeBase, job_description: str, resume: str):
    print("🎯 Tailoring resume for job...\n")
    relevant = kb.get_relevant_experience(job_description)

    tailor = ResumeTailorer()
    tailored = tailor.tailor_resume(resume, job_description, relevant)

    print("✨ Tailored Resume:")
    print(tailored)


def cmd_cover_letter(kb: KnowledgeBase, job_description: str, company: str):
    print(f"✍️ Generating cover letter for {company}...\n")
    relevant = kb.get_relevant_experience(job_description)

    generator = CoverLetterGenerator()
    letter = generator.generate(job_description, company, relevant)

    print("✨ Cover Letter:")
    print(letter)


async def cmd_search(keywords: str, location: str, limit: int = 5):
    print(f"🔍 Searching for '{keywords}' in '{location}'...\n")
    orchestrator = ScraperOrchestrator(headless=True)
    jobs = await orchestrator.search_all(keywords, location, limit_per_source=limit)

    for i, job in enumerate(jobs, 1):
        print(f"--- Job {i} ---")
        print(f"📌 {job.title} at {job.company}")
        print(f"📍 {job.location}")
        print(f"🔗 {job.url}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Job Application Agent")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("init", help="Initialize knowledge base directories")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest documents into knowledge base")
    ingest_parser.add_argument("--career", "-c", help="Path to career master document")

    query_parser = subparsers.add_parser("query", help="Query the knowledge base")
    query_parser.add_argument("query_text", help="Query string")
    query_parser.add_argument("--k", "-k", type=int, default=5, help="Number of results")

    search_parser = subparsers.add_parser("search", help="Search for jobs")
    search_parser.add_argument("keywords", help="Search keywords (e.g. Python Developer)")
    search_parser.add_argument("location", help="Job location (e.g. New York)")
    search_parser.add_argument("--limit", "-l", type=int, default=5, help="Limit per source")

    tailor_parser = subparsers.add_parser("tailor", help="Tailor resume for a job")
    tailor_parser.add_argument("--job", "-j", required=True, help="Job description")
    tailor_parser.add_argument("--resume", "-r", required=True, help="Resume text")

    cover_parser = subparsers.add_parser("cover", help="Generate cover letter")
    cover_parser.add_argument("--job", "-j", required=True, help="Job description")
    cover_parser.add_argument("--company", "-c", required=True, help="Company name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "init":
        setup_directories()
        print("✅ Directories initialized")
        return

    if args.command == "search":
        asyncio.run(cmd_search(args.keywords, args.location, args.limit))
        return

    kb = initialize_knowledge_base()

    if args.command == "ingest":
        cmd_ingest(kb, args.career)
    elif args.command == "query":
        cmd_query(kb, args.query_text, args.k)
    elif args.command == "tailor":
        cmd_tailor(kb, args.job, args.resume)
    elif args.command == "cover":
        cmd_cover_letter(kb, args.job, args.company)


if __name__ == "__main__":
    main()
