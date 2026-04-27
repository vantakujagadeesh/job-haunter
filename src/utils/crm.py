import sqlite3
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime


class ApplicationCRM:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "applications.db")
        
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    title TEXT,
                    company TEXT,
                    url TEXT,
                    source TEXT,
                    location TEXT,
                    salary TEXT,
                    ats_score INTEGER,
                    stage TEXT DEFAULT 'Saved',
                    applied_at TEXT,
                    email_sent INTEGER DEFAULT 0,
                    cover_letter TEXT,
                    tailored_resume TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_job(self, job: Dict[str, Any]) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO applications 
                (job_id, title, company, url, source, location, salary, ats_score, stage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.get("job_id", ""),
                job.get("title", ""),
                job.get("company", ""),
                job.get("url", ""),
                job.get("source", "Unknown"),
                job.get("location", ""),
                job.get("salary", ""),
                job.get("ats_score", 0),
                job.get("stage", "Saved")
            ))
            conn.commit()
            return cursor.lastrowid

    def update_stage(self, job_id: str, new_stage: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE applications 
                SET stage = ? 
                WHERE job_id = ? OR id = ?
            """, (new_stage, job_id, job_id))
            conn.commit()

    def update_ats(self, job_id: str, score: int, breakdown_json: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE applications 
                SET ats_score = ?, notes = COALESCE(notes, '') || ?
                WHERE job_id = ? OR id = ?
            """, (score, f"\nATS Breakdown: {breakdown_json}\n", job_id, job_id))
            conn.commit()

    def mark_applied(self, job_id: str, email_sent: bool = False):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE applications 
                SET stage = 'Applied', 
                    applied_at = ?, 
                    email_sent = ?
                WHERE job_id = ? OR id = ?
            """, (datetime.now().isoformat(), 1 if email_sent else 0, job_id, job_id))
            conn.commit()

    def get_kanban(self) -> Dict[str, List[Dict]]:
        stages = ["Saved", "Applied", "Interviewing", "Offers", "Rejected"]
        kanban = {stage: [] for stage in stages}
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications ORDER BY created_at DESC")
            
            for row in cursor.fetchall():
                job_dict = dict(row)
                stage = job_dict.get("stage", "Saved")
                if stage in kanban:
                    kanban[stage].append(job_dict)
        
        return kanban

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "total": 0,
            "applied": 0,
            "success_rate": 0.0,
            "by_source": {},
            "by_stage": {}
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM applications")
            stats["total"] = cursor.fetchone()["total"]
            
            cursor.execute("SELECT COUNT(*) as applied FROM applications WHERE stage = 'Applied' OR stage = 'Interviewing' OR stage = 'Offers'")
            stats["applied"] = cursor.fetchone()["applied"]
            
            if stats["total"] > 0:
                stats["success_rate"] = round((stats["applied"] / stats["total"]) * 100, 1)
            
            cursor.execute("SELECT source, COUNT(*) as count FROM applications GROUP BY source")
            for row in cursor.fetchall():
                stats["by_source"][row["source"]] = row["count"]
            
            cursor.execute("SELECT stage, COUNT(*) as count FROM applications GROUP BY stage")
            for row in cursor.fetchall():
                stats["by_stage"][row["stage"]] = row["count"]
        
        return stats

    def get_timeline(self, limit: int = 50) -> List[Dict]:
        timeline = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM applications 
                ORDER BY COALESCE(applied_at, created_at) DESC 
                LIMIT ?
            """, (limit,))
            
            for row in cursor.fetchall():
                timeline.append(dict(row))
        
        return timeline

    def export_json(self, filepath: str):
        data = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications")
            
            for row in cursor.fetchall():
                data.append(dict(row))
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath

    def search(self, query: str) -> List[Dict]:
        results = []
        search_term = f"%{query}%"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM applications 
                WHERE title LIKE ? OR company LIKE ?
                ORDER BY created_at DESC
            """, (search_term, search_term))
            
            for row in cursor.fetchall():
                results.append(dict(row))
        
        return results
