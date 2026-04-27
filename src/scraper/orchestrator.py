from typing import List, Dict, Optional
import asyncio
from .models import JobListing
from .linkedin_scraper import LinkedInScraper
from .mock_scraper import MockScraper
import logging

logger = logging.getLogger(__name__)

class ScraperOrchestrator:
    def __init__(self, headless: bool = True, use_mock: bool = True):
        self.scrapers = {}
        
        # Always add MockScraper as it's our only way to get Indeed/Naukri data reliably without blocks
        self.scrapers["mock"] = MockScraper(headless=headless)
        
        # Add LinkedIn for live search if possible
        self.scrapers["linkedin"] = LinkedInScraper(headless=headless)

    def _is_fake_job(self, job: JobListing) -> bool:
        """Filter out jobs that look suspicious."""
        if not job.description or len(job.description) < 100:
            return True
        if job.description == "Details pending...":
            return False # Allow these for now as we can fetch them
        
        suspicious_keywords = ["money fast", "work from home scam", "whatsapp me", "earn lakhs", "no experience needed urgent"]
        if any(kw in job.description.lower() for kw in suspicious_keywords):
            return True
        
        return False

    async def search_all(
        self,
        keywords: str,
        location: str,
        limit_per_source: int = 10,
        sources: Optional[List[str]] = None
    ) -> List[JobListing]:
        """Search across multiple job boards concurrently."""
        active_sources = sources if sources else list(self.scrapers.keys())
        tasks = []

        for source in active_sources:
            if source in self.scrapers:
                tasks.append(self.scrapers[source].search_jobs(keywords, location, limit_per_source))
            else:
                logger.warning(f"Source '{source}' not supported.")

        results = await asyncio.gather(*tasks)

        # Flatten the list of lists and filter out fakes
        all_jobs = []
        for sublist in results:
            for job in sublist:
                if not self._is_fake_job(job):
                    all_jobs.append(job)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job.url not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job.url)

        return unique_jobs

    async def get_full_details(self, job: JobListing) -> Optional[JobListing]:
        """Fetch full job details for a specific listing."""
        if job.source.lower() in self.scrapers:
            return await self.scrapers[job.source.lower()].extract_job_details(job.url)
        return None
