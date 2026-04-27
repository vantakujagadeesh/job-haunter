from playwright.async_api import async_playwright, Page
from typing import Dict, List, Optional, Any
from src.rag.llm_manager import LLMManager
import logging
import json

logger = logging.getLogger(__name__)

class FormFiller:
    def __init__(self, llm_manager: Optional[LLMManager] = None):
        self.llm = llm_manager or LLMManager(temperature=0.1)

    async def extract_form_fields(self, page: Page) -> List[Dict[str, Any]]:
        """Extract all visible input fields from the current page."""
        fields = await page.evaluate("""() => {
            const inputs = Array.from(document.querySelectorAll('input, select, textarea'));
            return inputs.map(input => ({
                id: input.id,
                name: input.name,
                placeholder: input.placeholder,
                type: input.type,
                label: document.querySelector(`label[for="${input.id}"]`)?.innerText || '',
                value: input.value,
                tagName: input.tagName
            })).filter(input => input.type !== 'hidden' && input.type !== 'submit');
        }""")
        return fields

    async def map_fields_to_user_data(self, fields: List[Dict], user_data: Dict) -> Dict[str, str]:
        """Use LLM to map form fields to user career data."""
        system_prompt = "You are an expert at mapping web form fields to user profile information."
        prompt = f"""Form Fields: {json.dumps(fields)}
        
        User Data: {json.dumps(user_data)}
        
        Map each form field (by ID or name) to the appropriate value from the User Data.
        Return ONLY a JSON object where keys are field names/IDs and values are the user data values.
        Example: {{"first_name": "John", "last_name": "Doe"}}"""

        response = self.llm.generate(prompt, system_prompt)
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            return json.loads(response)
        except:
            return {}

    async def fill_form(self, page: Page, field_mapping: Dict[str, str]):
        """Fill the form fields on the page based on the mapping."""
        for field_id, value in field_mapping.items():
            try:
                # Try to find by ID first, then name
                selector = f"#{field_id}" if field_id else f"[name='{field_id}']"
                if await page.query_selector(selector):
                    await page.fill(selector, str(value))
            except Exception as e:
                logger.warning(f"Could not fill field {field_id}: {e}")

    async def auto_apply_copilot(self, url: str, user_data: Dict):
        """Open a browser and help the user fill out the job application."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False) # Keep it visible for the user
            page = await browser.new_page()
            await page.goto(url)
            
            # This is where the user would interactively use the copilot
            # In a production app, we'd have a sidebar or overlay
            logger.info("Browser opened for application. Map fields manually or use automation tools.")
            
            # Keep browser open for user to review
            # await asyncio.sleep(60) 
            return page
