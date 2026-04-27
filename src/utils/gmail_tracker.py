import os
import os.path
import base64
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict, Optional

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailTracker:
    def __init__(self, token_path='data/token.json', credentials_path='config/credentials.json'):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None
        self.mock_mode = False
        
        if not os.path.exists('data'):
            os.makedirs('data')

    def authenticate(self):
        """Authenticates with Gmail API."""
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    self.mock_mode = True
                    return False, "config/credentials.json not found. Entering mock mode."
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
        
        return True, "Authenticated successfully"

    def fetch_recruiter_emails(self, max_results=10) -> List[Dict]:
        """Fetches recent emails that look like recruiter responses."""
        if self.mock_mode or not self.creds:
            return self._get_mock_emails()

        try:
            service = build('gmail', 'v1', credentials=self.creds)
            # Query for emails containing common recruiter keywords
            query = "interview OR 'job application' OR 'hiring' OR recruiter OR 'thank you for applying'"
            results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return []

            email_data = []
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for b in [headers] for h in b if h['name'] == 'Subject'), "No Subject")
                sender = next((h['value'] for b in [headers] for h in b if h['name'] == 'From'), "Unknown Sender")
                snippet = msg.get('snippet', '')
                date = next((h['value'] for b in [headers] for h in b if h['name'] == 'Date'), "Unknown Date")
                
                # Simple sentiment/category detection
                category = "General"
                lower_snippet = snippet.lower()
                if "interview" in lower_snippet or "schedule" in lower_snippet:
                    category = "Interview Request"
                elif "unfortunately" in lower_snippet or "not moving forward" in lower_snippet:
                    category = "Rejection"
                elif "thank you for applying" in lower_snippet:
                    category = "Confirmation"
                
                email_data.append({
                    "id": message['id'],
                    "subject": subject,
                    "sender": sender,
                    "snippet": snippet,
                    "date": date,
                    "category": category
                })

            return email_data

        except HttpError as error:
            print(f"An error occurred: {error}")
            return self._get_mock_emails()

    def _get_mock_emails(self) -> List[Dict]:
        return [
            {
                "id": "mock1",
                "subject": "Interview Request: Senior Python Engineer at TechCorp",
                "sender": "sarah.hr@techcorp.com",
                "snippet": "Hi John, we were impressed with your profile and would like to schedule a 30-minute introductory call...",
                "date": "Oct 24, 2023",
                "category": "Interview Request"
            },
            {
                "id": "mock2",
                "subject": "Update on your application for Data Scientist at InnovateAI",
                "sender": "hiring@innovateai.io",
                "snippet": "Thank you for your interest in InnovateAI. Unfortunately, we have decided to move forward with other candidates...",
                "date": "Oct 23, 2023",
                "category": "Rejection"
            },
            {
                "id": "mock3",
                "subject": "Thank you for applying to StartupXYZ",
                "sender": "no-reply@startupxyz.com",
                "snippet": "We have received your application for the Full Stack Developer position and will review it shortly...",
                "date": "Oct 22, 2023",
                "category": "Confirmation"
            }
        ]
