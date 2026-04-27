from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class JobListing:
    title: str
    company: str
    location: str
    url: str
    source: str = "LinkedIn"
    job_id: str = ""
    salary: str = ""
    posted: str = ""
    description: str = ""
    easy_apply: bool = False
    applied: bool = False
    apply_status: str = "pending"
    scraped_at: datetime = field(default_factory=datetime.now)


@dataclass
class NaukriJob(JobListing):
    experience: str = ""
    skills: List[str] = field(default_factory=list)


@dataclass
class IndeedJob(JobListing):
    pass


@dataclass
class WellfoundJob(JobListing):
    equity: str = ""
    stage: str = ""
