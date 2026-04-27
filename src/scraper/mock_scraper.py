from typing import List, Optional
from .base_scraper import BaseScraper
from .models import JobListing
import uuid
from datetime import datetime

class MockScraper(BaseScraper):
    """A mock scraper that returns realistic job data for multiple sources."""

    async def search_jobs(self, keywords: str, location: str, limit: int = 5) -> List[JobListing]:
        sources = ["LinkedIn", "Indeed", "Naukri"]
        sample_jobs = []
        
        for source in sources:
            sample_jobs.append({
                "title": f"Senior {keywords}",
                "company": f"{source} Partner - TechCorp",
                "location": location,
                "description": f"High-quality role from {source}. We are looking for a Senior {keywords} with expertise in Python, Cloud, and AI. This is a verified position with competitive benefits.",
                "source": source,
                "url": f"https://{source.lower()}.com/jobs/{uuid.uuid4()}"
            })
            sample_jobs.append({
                "title": f"{keywords} Specialist",
                "company": f"Global {source} Client",
                "location": "Remote",
                "description": f"Join our global team as a {keywords} Specialist. Sourced via {source}. Requires 3+ years of experience and strong communication skills.",
                "source": source,
                "url": f"https://{source.lower()}.com/jobs/{uuid.uuid4()}"
            })

        jobs = []
        # Take a mix of sources up to the limit
        for i in range(min(limit, len(sample_jobs))):
            data = sample_jobs[i]
            jobs.append(JobListing(
                id=str(uuid.uuid4()),
                title=data["title"],
                company=data["company"],
                location=data["location"],
                description=data["description"],
                url=data["url"],
                source=data["source"]
            ))
        return jobs

    async def extract_job_details(self, url: str) -> Optional[JobListing]:
        return JobListing(
            id=str(uuid.uuid4()),
            title="Mock Job",
            company="Mock Co",
            description="This is a full mock description for testing.",
            url=url,
            source="MockSource"
        )
