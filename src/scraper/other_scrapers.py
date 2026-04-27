import asyncio
import json
import random
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from .models import NaukriJob, IndeedJob, WellfoundJob, JobListing
import logging

logger = logging.getLogger(__name__)


class NaukriScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.mock_mode = True
        self.data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

    async def _human_delay(self, min_ms: int = 400, max_ms: int = 1200):
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)

    async def start(self):
        return (True, "Scraper started")

    async def stop(self):
        return (True, "Scraper stopped")

    async def login(self, email: str, password: str) -> Tuple[bool, str]:
        return (True, "Mock login successful")

    async def search_jobs(self, keywords: str, location: str, experience_years: int = 2, limit: int = 10) -> List[NaukriJob]:
        return self._get_mock_jobs(keywords, location, limit)

    async def apply_to_job(self, job: JobListing, applicant: Dict, resume_path: str) -> Tuple[bool, str]:
        await asyncio.sleep(2)
        return (True, "Mock application submitted to Naukri")

    def _get_mock_jobs(self, keywords: str, location: str, limit: int) -> List[NaukriJob]:
        mock_jobs = [
            NaukriJob(
                title=f"{keywords} Developer",
                company="Naukri Tech Solutions",
                location=location,
                url="https://www.naukri.com/job-listings-mock-1",
                source="Naukri",
                experience="3-5 years",
                salary="₹8-12 LPA",
                skills=["Python", "Django", "AWS"]
            ),
            NaukriJob(
                title=f"Senior {keywords} Engineer",
                company="IndiaCorp",
                location=f"{location}, India",
                url="https://www.naukri.com/job-listings-mock-2",
                source="Naukri",
                experience="5-8 years",
                salary="₹15-20 LPA",
                skills=["Python", "FastAPI", "Docker", "Kubernetes"]
            )
        ]
        return mock_jobs[:limit]


class IndeedScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.mock_mode = True

    async def _human_delay(self, min_ms: int = 400, max_ms: int = 1200):
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)

    async def start(self):
        return (True, "Scraper started")

    async def stop(self):
        return (True, "Scraper stopped")

    async def search_jobs(self, keywords: str, location: str, limit: int = 10) -> List[IndeedJob]:
        return self._get_mock_jobs(keywords, location, limit)

    async def apply_to_job(self, job: JobListing, applicant: Dict, resume_path: str) -> Tuple[bool, str]:
        await asyncio.sleep(2)
        return (True, "Mock application submitted to Indeed")

    def _get_mock_jobs(self, keywords: str, location: str, limit: int) -> List[IndeedJob]:
        mock_jobs = [
            IndeedJob(
                title=f"{keywords} Engineer",
                company="Indeed Global",
                location=location,
                url="https://in.indeed.com/viewjob?jk=mock1",
                source="Indeed",
                salary="$70k-$90k",
                posted="3 days ago"
            ),
            IndeedJob(
                title=f"Full Stack {keywords} Developer",
                company="Tech Giants Inc.",
                location=f"{location} (Remote)",
                url="https://in.indeed.com/viewjob?jk=mock2",
                source="Indeed",
                salary="$85k-$110k",
                posted="1 day ago"
            )
        ]
        return mock_jobs[:limit]


class WellfoundScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.mock_mode = True
        self.data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

    async def _human_delay(self, min_ms: int = 400, max_ms: int = 1200):
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)

    async def start(self):
        return (True, "Scraper started")

    async def stop(self):
        return (True, "Scraper stopped")

    async def login(self, email: str, password: str) -> Tuple[bool, str]:
        return (True, "Mock login successful")

    async def search_jobs(self, keywords: str, location: str = "Remote", limit: int = 10) -> List[WellfoundJob]:
        return self._get_mock_jobs(keywords, location, limit)

    async def apply_to_job(self, job: JobListing, applicant: Dict, resume_path: str) -> Tuple[bool, str]:
        await asyncio.sleep(2)
        return (True, "Mock application submitted to Wellfound")

    def _get_mock_jobs(self, keywords: str, location: str, limit: int) -> List[WellfoundJob]:
        mock_jobs = [
            WellfoundJob(
                title=f"{keywords} Engineer",
                company="StartupABC",
                location=location,
                url="https://wellfound.com/jobs/mock1",
                source="Wellfound",
                salary="$100k-$140k",
                equity="0.1%-0.3%",
                stage="Series A"
            ),
            WellfoundJob(
                title=f"Senior {keywords}",
                company="UnicornXYZ",
                location=location,
                url="https://wellfound.com/jobs/mock2",
                source="Wellfound",
                salary="$150k-$200k",
                equity="0.2%-0.5%",
                stage="Series C"
            )
        ]
        return mock_jobs[:limit]
