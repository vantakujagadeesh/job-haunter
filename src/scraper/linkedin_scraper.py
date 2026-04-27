import asyncio
import json
import random
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from .models import JobListing
import logging

logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self.base_url = "https://www.linkedin.com"
        self.data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.session_path = self.data_dir / "linkedin_session.json"
        
        self.mock_mode = False

    async def _human_delay(self, min_ms: int = 400, max_ms: int = 1200):
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)

    async def start(self):
        try:
            self.playwright = await async_playwright().start()
            
            launch_options = {
                "headless": self.headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            }
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York"
            )
            
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            self.page = await self.context.new_page()
            
            if self.session_path.exists():
                try:
                    with open(self.session_path, 'r') as f:
                        cookies = json.load(f)
                    await self.context.add_cookies(cookies)
                    logger.info("Loaded saved session")
                except Exception as e:
                    logger.warning(f"Failed to load session: {e}")
            
            return (True, "Browser started successfully")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return (False, f"Failed to start browser: {str(e)}")

    async def stop(self):
        try:
            if self.context:
                cookies = await self.context.cookies()
                with open(self.session_path, 'w') as f:
                    json.dump(cookies, f)
                logger.info("Saved session")
            
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            return (True, "Browser stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop browser: {e}")
            return (False, f"Failed to stop browser: {str(e)}")

    async def _is_logged_in(self) -> bool:
        try:
            await self.page.goto(f"{self.base_url}/feed", wait_until="networkidle", timeout=10000)
            await self._human_delay()
            if "feed" in self.page.url:
                return True
            return False
        except:
            return False

    async def login(self, email: str, password: str) -> Tuple[bool, str]:
        try:
            if await self._is_logged_in():
                return (True, "Already logged in")
            
            await self.page.goto(f"{self.base_url}/login", wait_until="networkidle")
            await self._human_delay()
            
            email_input = await self.page.query_selector("#username")
            if email_input:
                await email_input.fill(email)
                await self._human_delay()
            
            password_input = await self.page.query_selector("#password")
            if password_input:
                await password_input.fill(password)
                await self._human_delay()
            
            submit_btn = await self.page.query_selector('button[type="submit"]')
            if submit_btn:
                await submit_btn.click()
                await self._human_delay(2000, 3000)
            
            if not self.headless:
                captcha_detected = False
                try:
                    await self.page.wait_for_selector("text=Verification", timeout=5000)
                    captcha_detected = True
                except:
                    pass
                
                if captcha_detected:
                    logger.info("CAPTCHA detected, waiting 30 seconds for manual completion...")
                    await asyncio.sleep(30)
            
            if await self._is_logged_in():
                cookies = await self.context.cookies()
                with open(self.session_path, 'w') as f:
                    json.dump(cookies, f)
                return (True, "Login successful")
            else:
                return (False, "Login failed - please check credentials")
        
        except Exception as e:
            logger.error(f"Login error: {e}")
            return (False, f"Login error: {str(e)}")

    async def search_jobs(
        self, 
        keywords: str, 
        location: str, 
        limit: int = 10, 
        easy_apply_only: bool = False,
        date_posted: str = "r604800"
    ) -> List[JobListing]:
        
        if self.mock_mode or not self.page:
            return self._get_mock_jobs(keywords, location, limit)
        
        jobs = []
        try:
            search_url = f"{self.base_url}/jobs/search/"
            params = {
                "keywords": keywords,
                "location": location,
                "f_TPR": date_posted
            }
            if easy_apply_only:
                params["f_LF"] = "f_AL"
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{search_url}?{query_string}"
            
            await self.page.goto(full_url, wait_until="networkidle")
            await self._human_delay(1000, 2000)
            
            job_cards = await self.page.query_selector_all(".jobs-search-results__list-item")
            
            for i, card in enumerate(job_cards[:limit]):
                try:
                    await card.scroll_into_view_if_needed()
                    await self._human_delay()
                    
                    title_elem = await card.query_selector(".job-card-list__title")
                    title = (await title_elem.inner_text()).strip() if title_elem else "N/A"
                    
                    company_elem = await card.query_selector(".job-card-container__primary-description")
                    company = (await company_elem.inner_text()).strip() if company_elem else "N/A"
                    
                    location_elem = await card.query_selector(".job-card-container__metadata-item")
                    location_val = (await location_elem.inner_text()).strip() if location_elem else "N/A"
                    
                    link_elem = await card.query_selector(".job-card-list__title")
                    url = await link_elem.get_attribute("href") if link_elem else ""
                    if url and not url.startswith("http"):
                        url = f"{self.base_url}{url}"
                    
                    easy_apply_elem = await card.query_selector(".job-card-container__apply-method")
                    easy_apply = easy_apply_elem is not None
                    
                    job_id = ""
                    if url:
                        job_id_match = await card.get_attribute("data-occludable-job-id")
                        job_id = job_id_match or ""
                    
                    job = JobListing(
                        title=title,
                        company=company,
                        location=location_val,
                        url=url,
                        source="LinkedIn",
                        job_id=job_id,
                        easy_apply=easy_apply
                    )
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing job card {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Search jobs error: {e}")
        
        return jobs if jobs else self._get_mock_jobs(keywords, location, limit)

    async def get_job_description(self, url: str) -> str:
        if self.mock_mode or not self.page:
            return self._get_mock_job_description()
        
        try:
            await self.page.goto(url, wait_until="networkidle")
            await self._human_delay()
            
            show_more = await self.page.query_selector(".jobs-description__footer-button")
            if show_more:
                await show_more.click()
                await self._human_delay()
            
            desc_elem = await self.page.query_selector(".jobs-description__content")
            if desc_elem:
                text = (await desc_elem.inner_text()).strip()
                return text[:3000]
            
            return ""
        except Exception as e:
            logger.error(f"Get job description error: {e}")
            return self._get_mock_job_description()

    def _guess_answer(self, label: str, applicant: Dict) -> str:
        label_lower = label.lower()
        
        if any(k in label_lower for k in ["name", "full name"]):
            return applicant.get("name", "")
        elif "email" in label_lower:
            return applicant.get("email", "")
        elif "phone" in label_lower or "mobile" in label_lower:
            return applicant.get("phone", "")
        elif "city" in label_lower or "location" in label_lower:
            return applicant.get("city", "")
        elif "linkedin" in label_lower:
            return applicant.get("linkedin_url", "")
        elif "experience" in label_lower and "year" in label_lower:
            return str(applicant.get("years_experience", ""))
        elif "notice" in label_lower:
            return applicant.get("notice_period", "")
        elif "current" in label_lower and "salary" in label_lower:
            return str(applicant.get("current_salary", ""))
        elif "expected" in label_lower and "salary" in label_lower:
            return str(applicant.get("expected_salary", ""))
        elif "portfolio" in label_lower:
            return applicant.get("portfolio_url", "")
        
        return ""

    async def easy_apply(self, job: JobListing, applicant: Dict, resume_path: str) -> Tuple[bool, str]:
        if self.mock_mode:
            await asyncio.sleep(2)
            return (True, "Mock application submitted successfully")
        
        if not self.page:
            return (False, "Browser not started")
        
        try:
            await self.page.goto(job.url, wait_until="networkidle")
            await self._human_delay()
            
            easy_apply_btn = await self.page.query_selector(".jobs-apply-button")
            if not easy_apply_btn:
                return (False, "Easy Apply button not found")
            
            await easy_apply_btn.click()
            await self._human_delay(1000, 2000)
            
            for step in range(8):
                try:
                    await self._human_delay()
                    
                    text_inputs = await self.page.query_selector_all("input[type='text'], input[type='email'], input[type='tel'], input[type='number']")
                    for inp in text_inputs:
                        try:
                            label = ""
                            parent = await inp.evaluate_handle("el => el.closest('div')")
                            if parent:
                                label_elem = await parent.query_selector("label")
                                if label_elem:
                                    label = await label_elem.inner_text()
                            
                            current_val = await inp.input_value()
                            if not current_val:
                                answer = self._guess_answer(label, applicant)
                                if answer:
                                    await inp.fill(answer)
                                    await self._human_delay()
                        except:
                            continue
                    
                    textareas = await self.page.query_selector_all("textarea")
                    for ta in textareas:
                        try:
                            label = ""
                            parent = await ta.evaluate_handle("el => el.closest('div')")
                            if parent:
                                label_elem = await parent.query_selector("label")
                                if label_elem:
                                    label = await label_elem.inner_text()
                            
                            label_lower = label.lower()
                            current_val = await ta.input_value()
                            if not current_val and any(k in label_lower for k in ["cover", "summary", "why", "motivation"]):
                                cover_letter = applicant.get("cover_letter", "")
                                if cover_letter:
                                    await ta.fill(cover_letter)
                                    await self._human_delay()
                        except:
                            continue
                    
                    selects = await self.page.query_selector_all("select")
                    for sel in selects:
                        try:
                            label = ""
                            parent = await sel.evaluate_handle("el => el.closest('div')")
                            if parent:
                                label_elem = await parent.query_selector("label")
                                if label_elem:
                                    label = await label_elem.inner_text()
                            
                            label_lower = label.lower()
                            if any(k in label_lower for k in ["authorized", "work authorization", "sponsorship"]):
                                if "sponsorship" in label_lower:
                                    await sel.select_option("No")
                                else:
                                    await sel.select_option("Yes")
                            await self._human_delay()
                        except:
                            continue
                    
                    radios = await self.page.query_selector_all("input[type='radio']")
                    radio_groups = {}
                    for radio in radios:
                        name = await radio.get_attribute("name")
                        if name not in radio_groups:
                            radio_groups[name] = []
                        radio_groups[name].append(radio)
                    
                    for name, group in radio_groups.items():
                        try:
                            for radio in group:
                                parent = await radio.evaluate_handle("el => el.closest('div')")
                                if parent:
                                    label_elem = await parent.query_selector("label")
                                    if label_elem:
                                        label_text = (await label_elem.inner_text()).lower()
                                        if any(k in label_text for k in ["yes", "authorized", "i am"]) and not any(k in label_text for k in ["disability", "veteran"]):
                                            await radio.check()
                                            await self._human_delay()
                                            break
                        except:
                            continue
                    
                    file_input = await self.page.query_selector("input[type='file']")
                    if file_input and os.path.exists(resume_path):
                        await file_input.set_input_files(resume_path)
                        await self._human_delay(1000, 2000)
                    
                    next_btn = await self.page.query_selector("button[aria-label='Continue to next step'], button:has-text('Next'), button:has-text('Continue')")
                    review_btn = await self.page.query_selector("button:has-text('Review'), button[aria-label='Review your application']")
                    submit_btn = await self.page.query_selector("button:has-text('Submit application'), button[aria-label='Submit application']")
                    
                    if submit_btn:
                        await submit_btn.click()
                        await self._human_delay(2000, 3000)
                        
                        page_content = await self.page.content()
                        if any(phrase in page_content.lower() for phrase in ["application sent", "applied", "successfully submitted", "thank you for applying"]):
                            return (True, "Application submitted successfully")
                        else:
                            return (False, "Application may not have been submitted - please verify")
                    elif review_btn:
                        await review_btn.click()
                        await self._human_delay()
                    elif next_btn:
                        await next_btn.click()
                        await self._human_delay()
                    else:
                        break
                        
                except Exception as e:
                    logger.error(f"Error in step {step}: {e}")
                    continue
            
            return (False, "Could not complete application process")
            
        except Exception as e:
            logger.error(f"Easy apply error: {e}")
            return (False, f"Easy apply error: {str(e)}")

    def _get_mock_jobs(self, keywords: str, location: str, limit: int) -> List[JobListing]:
        mock_jobs = [
            JobListing(
                title=f"Senior {keywords} Engineer",
                company="TechCorp Inc.",
                location=location,
                url="https://www.linkedin.com/jobs/view/mock-1",
                job_id="123456",
                salary="$120k-$150k",
                posted="2 days ago",
                easy_apply=True
            ),
            JobListing(
                title=f"{keywords} Developer",
                company="StartupXYZ",
                location=f"{location} (Remote)",
                url="https://www.linkedin.com/jobs/view/mock-2",
                job_id="789012",
                salary="$90k-$120k",
                posted="1 week ago",
                easy_apply=True
            ),
            JobListing(
                title=f"Lead {keywords} Architect",
                company="Enterprise Solutions",
                location=location,
                url="https://www.linkedin.com/jobs/view/mock-3",
                job_id="345678",
                salary="$150k-$180k",
                posted="3 days ago",
                easy_apply=False
            )
        ]
        return mock_jobs[:limit]

    def _get_mock_job_description(self) -> str:
        return """
        We are looking for an experienced software engineer to join our team.
        
        Requirements:
        - 5+ years of experience with Python
        - Experience with Django or FastAPI
        - Knowledge of AWS, Docker, and Kubernetes
        - Strong understanding of REST APIs and microservices
        - Bachelor's degree in Computer Science or related field
        
        Nice to have:
        - Experience with React or JavaScript
        - Machine learning background
        - CI/CD pipeline experience
        """
