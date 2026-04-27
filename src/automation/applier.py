from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Page, Browser, ElementHandle
import logging
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class JobApplier:
    def __init__(self, headless: bool = False):
        self.headless = headless

    async def apply(self, job_url: str, user_data: Dict[str, Any], resume_path: str, cover_letter: Optional[str] = None):
        """
        FULLY AUTOMATIC bulk application: fill form and try to submit automatically!
        Closes after processing so bulk can continue.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
            
            try:
                logger.info(f"Starting FULL AUTO application for {job_url}")
                
                # Navigate
                try:
                    await page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    logger.warning("Page load timeout, trying to proceed.")
                
                # 1. Find and click Apply
                await self._find_and_click_apply(page)
                await page.wait_for_timeout(1500)
                
                # 2. Fill all fields
                await self._fill_all_visible_fields(page, user_data, resume_path, cover_letter)
                await page.wait_for_timeout(1000)
                
                # 3. TRY TO SUBMIT AUTOMATICALLY! (TickBig style!)
                submit_clicked = await self._try_submit(page)
                
                logger.info(f"Application for {job_url} done. Submit clicked: {submit_clicked}")
                
                # Wait a sec, then CLOSE so bulk can continue
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error during auto-application: {e}")
            finally:
                # ALWAYS CLOSE BROWSER for bulk applications!
                try:
                    if browser.is_connected():
                        await browser.close()
                except:
                    pass

    async def _find_and_click_apply(self, page: Page) -> bool:
        selectors = [
            "button:has-text('Apply')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply')",
            ".jobs-apply-button",
            "button.apply-button",
            "[data-automation='job-apply-button']",
            "button[aria-label*='Apply']"
        ]
        for selector in selectors:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    return True
            except: continue
        return False

    async def _find_navigation_button(self, page: Page) -> Optional[ElementHandle]:
        selectors = [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button:has-text('Submit')",
            "button:has-text('Review')",
            "input[type='submit']",
            "button.continue-button"
        ]
        for selector in selectors:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    return btn
            except: continue
        return None
    
    async def _try_submit(self, page: Page) -> bool:
        """TickBig-style: Try to click Submit/Continue automatically!"""
        submit_selectors = [
            "button:has-text('Submit Application')",
            "button:has-text('Submit')",
            "input[type='submit']",
            "button:has-text('Send')",
            "button:has-text('Apply Now')",
            "[type='submit']"
        ]
        
        for selector in submit_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    logger.info(f"Clicked submit button: {selector}")
                    await page.wait_for_timeout(2000)
                    return True
            except Exception as e:
                continue
        return False

    async def _fill_all_visible_fields(self, page: Page, data: Dict[str, Any], resume_path: str, cover_letter: Optional[str] = None):
        # 1. Standard text fields
        mappings = {
            "first_name": ["first", "given"],
            "last_name": ["last", "family"],
            "email": ["email", "e-mail"],
            "phone": ["phone", "tel", "mobile"],
            "location": ["location", "city", "address"]
        }
        
        inputs = await page.query_selector_all("input:not([type='hidden']), textarea")
        for field in inputs:
            if not await field.is_visible(): continue
            
            # Check ID, Name, Placeholder, Aria-label
            id_attr = (await field.get_attribute("id") or "").lower()
            name_attr = (await field.get_attribute("name") or "").lower()
            placeholder = (await field.get_attribute("placeholder") or "").lower()
            aria_label = (await field.get_attribute("aria-label") or "").lower()
            
            full_meta = f"{id_attr} {name_attr} {placeholder} {aria_label}"
            
            # Match data keys
            for key, keywords in mappings.items():
                if any(kw in full_meta for kw in keywords):
                    val = data.get(key)
                    if val:
                        await field.fill(val)
                        break
            
            # Special case for resume upload
            if 'resume' in full_meta or 'cv' in full_meta:
                type_attr = await field.get_attribute("type")
                if type_attr == "file":
                    await field.set_input_files(resume_path)
                elif 'text' in (type_attr or ""):
                    # Some forms ask for a link or text version
                    pass

        # 2. File uploads (if not handled above)
        file_inputs = await page.query_selector_all("input[type='file']")
        for f_input in file_inputs:
            if not await f_input.is_visible(): continue
            aria = (await f_input.get_attribute("aria-label") or "").lower()
            if 'resume' in aria or 'cv' in aria:
                await f_input.set_input_files(resume_path)
