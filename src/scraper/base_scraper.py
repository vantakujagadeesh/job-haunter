import asyncio
from typing import List, Optional
from abc import ABC, abstractmethod
from .models import JobListing
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    def __init__(self, headless: bool = True):
        self.headless = headless

    @abstractmethod
    async def search_jobs(self, keywords: str, location: str, limit: int = 10) -> List[JobListing]:
        """Search for jobs on the specific platform."""
        pass

    @abstractmethod
    async def extract_job_details(self, url: str) -> Optional[JobListing]:
        """Extract full details from a single job posting URL."""
        pass

    async def get_page_content(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            await browser.close()
            return content
