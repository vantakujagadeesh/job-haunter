import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from src.scraper.models import JobListing

class ApplicationTracker:
    def __init__(self, storage_file: str = "data/applications.json"):
        self.storage_file = storage_file
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump([], f)

    def _load_applications(self) -> List[Dict]:
        with open(self.storage_file, 'r') as f:
            return json.load(f)

    def _save_applications(self, apps: List[Dict]):
        with open(self.storage_file, 'w') as f:
            json.dump(apps, f, indent=4)

    def add_application(self, job: JobListing, status: str = "Discovered"):
        apps = self._load_applications()

        # Check if already exists
        for app in apps:
            if app["url"] == job.url:
                return

        new_app = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "url": job.url,
            "source": job.source,
            "status": status,
            "scraped_at": job.scraped_at.isoformat(),
            "last_updated": datetime.now().isoformat(),
            "notes": ""
        }

        apps.append(new_app)
        self._save_applications(apps)

    def update_status(self, job_url: str, new_status: str):
        apps = self._load_applications()
        for app in apps:
            if app["url"] == job_url:
                app["status"] = new_status
                app["last_updated"] = datetime.now().isoformat()
                break
        self._save_applications(apps)

    def get_all_applications(self) -> List[Dict]:
        return self._load_applications()

    def delete_application(self, job_url: str):
        apps = self._load_applications()
        apps = [app for app in apps if app["url"] != job_url]
        self._save_applications(apps)
