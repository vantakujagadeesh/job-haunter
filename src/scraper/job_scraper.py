from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime
from dataclasses import dataclass, asdict
import json
import os

@dataclass
class JobListing:
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_date: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None
    source: str = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, directory: str):
        os.makedirs(directory, exist_ok=True)
        filename = re.sub(r'[^\w\s-]', '', f"{self.company}_{self.title}".lower().replace(' ', '_'))[:100]
        filepath = os.path.join(directory, f"{filename}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class JobScraper:
    def __init__(self, headers: Optional[dict] = None):
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_indeed(
        self,
        job_title: str,
        location: str = "",
        num_pages: int = 1
    ) -> List[JobListing]:
        jobs = []
        base_url = "https://www.indeed.com/jobs"

        for page in range(num_pages):
            params = {
                "q": job_title,
                "l": location,
                "start": page * 10
            }
            try:
                response = self.session.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'lxml')

                job_cards = soup.select('div.job_seen_beacon')
                for card in job_cards:
                    job = self._parse_indeed_card(card)
                    if job:
                        jobs.append(job)

            except Exception as e:
                print(f"Error scraping page {page + 1}: {e}")
                continue

        return jobs

    def _parse_indeed_card(self, card) -> Optional[JobListing]:
        try:
            title_elem = card.select_one('h2.jobTitle > a, a.jobtitle')
            company_elem = card.select_one('span.companyName, a.companyName')
            location_elem = card.select_one('div.companyLocation, span.location')
            date_elem = card.select_one('span.date')
            salary_elem = card.select_one('div.salary-snippet, span.salary')
            link_elem = card.select_one('a.jcs-JobTitle')

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            location = location_elem.get_text(strip=True) if location_elem else "Not specified"
            url = urljoin("https://www.indeed.com", link_elem.get('href', '')) if link_elem else ""

            return JobListing(
                title=title,
                company=company,
                location=location,
                description="",
                url=url,
                source="indeed"
            )
        except Exception as e:
            print(f"Error parsing Indeed card: {e}")
            return None

    def scrape_linkedin_basic(
        self,
        job_title: str,
        location: str = "",
        num_pages: int = 1
    ) -> List[JobListing]:
        jobs = []
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPOST"

        for page in range(num_pages):
            params = {
                "keywords": job_title,
                "location": location,
                "startIndex": page * 25
            }
            try:
                response = self.session.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'lxml')

                job_cards = soup.select('li.jobs-search-results__list-item')
                for card in job_cards:
                    job = self._parse_linkedin_card(card)
                    if job:
                        jobs.append(job)

            except Exception as e:
                print(f"Error scraping LinkedIn page {page + 1}: {e}")
                continue

        return jobs

    def _parse_linkedin_card(self, card) -> Optional[JobListing]:
        try:
            title_elem = card.select_one('h3.base-search-card__title')
            company_elem = card.select_one('h4.base-search-card__subtitle')
            location_elem = card.select_one('span.job-search-card__location')
            link_elem = card.select_one('a.base-search-card__link')

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            location = location_elem.get_text(strip=True) if location_elem else "Not specified"
            url = link_elem.get('href', '') if link_elem else ""

            return JobListing(
                title=title,
                company=company,
                location=location,
                description="",
                url=url,
                source="linkedin"
            )
        except Exception as e:
            print(f"Error parsing LinkedIn card: {e}")
            return None

    def get_job_details(self, url: str) -> str:
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')

            description_elem = soup.select_one(
                'div.jobsearch-JobComponent-embeddedBody, '
                'div.description__text, '
                'div[id="job-details"], '
                'section.jobs-section'
            )

            if description_elem:
                return description_elem.get_text(separator='\n', strip=True)

            return ""

        except Exception as e:
            print(f"Error fetching job details: {e}")
            return ""

    def save_jobs(self, jobs: List[JobListing], directory: str):
        os.makedirs(directory, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        all_jobs_data = [job.to_dict() for job in jobs]

        filename = f"jobs_{timestamp}.json"
        filepath = os.path.join(directory, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(all_jobs_data, f, indent=2, ensure_ascii=False)

        for job in jobs:
            job.save(directory)

        print(f"Saved {len(jobs)} jobs to {directory}")
        return filepath
