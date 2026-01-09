import asyncio
import logging
from typing import Dict, Optional, List, Union
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SGMADocumentHunter:
    """
    A robust agent tool for locating and extracting PDF URLs from the 
    California DWR SGMA Portal.
    
    This class handles:
    1. Navigation to the SGMA 'Submitted Reports' page.
    2. Dynamic mapping of table columns (resilient to layout changes).
    3. Heuristic selection of the latest available Annual Report.
    4. Deep-linking to the specific Basin Status page to harvest PDF links.
    """

    BASE_URL = "https://sgma.water.ca.gov/portal/gspar/submitted"
    DOMAIN = "https://sgma.water.ca.gov"

    async def get_basin_documents(self, basin_identifier: str) -> Dict[str, Union[str, int, None]]:
        """
        Main entry point. Finds the latest Annual Report and GSP PDF for a given basin.

        Args:
            basin_identifier (str): The Basin Name (e.g., "Santa Cruz") or Code (e.g., "3-001").

        Returns:
            Dict: A dictionary containing:
                - basin_name (str): The full name found in the table.
                - latest_year (int): The year of the report found (e.g., 2024).
                - annual_report_url (str): Direct link to the Annual Report PDF.
                - gsp_url (str): Direct link to the GSP PDF (if found).
        """
        async with async_playwright() as p:
            # Launch browser (headless=True for servers, False to debug visually)
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # --- Step 1: Find the Basin's Status Page URL ---
                target_url, latest_year, full_basin_name = await self._find_basin_page(page, basin_identifier)
                
                if not target_url:
                    logger.warning(f"No reports found for identifier: {basin_identifier}")
                    return {}

                logger.info(f"Found {latest_year} report for '{full_basin_name}'. navigating to: {target_url}")

                # --- Step 2: Harvest PDFs from the Detail Page ---
                documents = await self._harvest_pdfs(page, target_url, latest_year)
                
                # Merge metadata
                documents.update({
                    "basin_name": full_basin_name,
                    "latest_year": latest_year
                })
                
                return documents

            finally:
                await browser.close()

    async def _find_basin_page(self, page: Page, identifier: str) -> tuple[Optional[str], int, str]:
        """
        Uses the table's Search Box with robust Year parsing and Debug logging.
        """
        import re # Import regex for safer number extraction

        await page.goto(self.BASE_URL)
        await page.wait_for_selector("table", timeout=15000)
        
        # 1. Map Headers
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        table = soup.find("table")
        header_row = table.find("thead").find("tr") if table.find("thead") else table.find("tr")
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
        
        try:
            basin_idx = next(i for i, h in enumerate(headers) if "basin" in h)
            year_idx = next(i for i, h in enumerate(headers) if "year" in h)
        except StopIteration:
            logger.error("❌ Could not map headers.")
            return None, 0, ""

        # 2. APPLY FILTER
        logger.info(f"🔍 Filtering table for '{identifier}'...")
        search_box = page.locator("input[type='search']")
        await search_box.wait_for(state="visible")
        await search_box.fill(identifier)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000) 
        
        # 3. READ RESULTS
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        rows = soup.find("table").find_all("tr")[1:] 
        
        logger.info(f"   -> Filter applied. Found {len(rows)} visible rows.")

        best_url = None
        max_year = 0
        found_name = ""

        for row in rows:
            cols = row.find_all("td")
            if len(cols) <= max(basin_idx, year_idx): continue
            
            row_basin_text = cols[basin_idx].get_text(strip=True)
            row_year_text = cols[year_idx].get_text(strip=True) # Read raw year text

            # Check Match
            if identifier.lower() in row_basin_text.lower():
                try:
                    # IMPROVED PARSING: Look for 4 digits in the text (e.g. handles "2024 (Draft)")
                    year_match = re.search(r'\d{4}', row_year_text)
                    if not year_match:
                        logger.warning(f"     ⚠️ Skipping Row: Year text '{row_year_text}' has no valid year.")
                        continue
                        
                    year = int(year_match.group(0))
                    
                    # Check Link
                    link_tag = cols[basin_idx].find("a")
                    if not link_tag or not link_tag.get('href'):
                        logger.warning(f"     ⚠️ Skipping Row: Year {year} has no clickable link.")
                        continue

                    # Success Logic
                    logger.info(f"     ✅ Valid Candidate: Year {year} | {row_basin_text}")
                    
                    if year >= max_year: # Use >= to capture the latest
                        max_year = year
                        found_name = row_basin_text
                        best_url = self.DOMAIN + link_tag['href']

                except Exception as e:
                    logger.error(f"     ❌ Error parsing row: {e}")
                    continue
            else:
                 # Just to see what else is in the table (noise)
                 pass

        return best_url, max_year, found_name
    
    async def _harvest_pdfs(self, page: Page, url: str, year: int) -> Dict[str, Optional[str]]:
        """
        Visits the basin page and extracts links using the specific filename pattern
        observed by the user (e.g., '3-001_WY_2024.pdf').
        """
        logger.info(f"   -> Harvesting PDFs from: {url}")
        
        # --- 1. Load Page (Lenient wait) ---
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_selector("a", timeout=5000) # Wait for at least some links
        except Exception as e:
            logger.warning(f"   ⚠️ Page load warning: {e}")

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        docs = {
            "annual_report_url": None,
            "gsp_url": None
        }
        # --- 2. Find Annual Report PDF ---    
        # --- STRATEGY 1: The "Text Pattern" Match (The Fix) ---
        # Look for a link where the TEXT contains "WY_2024" (or similar)
        # We search for the pattern in the TEXT, not the HREF.
        target_pattern = f"WY_{year}"
        
        # We use a lambda on the TAG to check its .get_text() content
        pdf_link = soup.find("a", string=lambda text: text and target_pattern in text and ".pdf" in text.lower())
        
        if pdf_link:
            # Found it! Now grab the href (which will be the ID, e.g., .../document/4478)
            docs["annual_report_url"] = self.DOMAIN + pdf_link['href']
            logger.info(f"      ✅ Found Annual Report (Text Match): {pdf_link.get_text(strip=True)}")
            
        else:
            # --- STRATEGY 2: The "Header" Fallback ---
            logger.info("      ℹ️ Text pattern match failed. Trying section lookup...")
            
            # Find the header "Annual Report PDF(s)"
            header = soup.find(string=lambda t: t and "Annual Report PDF" in t)
            if header:
                # The links are usually in the same container or the next one
                container = header.find_parent("div") or header.find_parent("td")
                
                if container:
                    # Find ANY link that looks like a file in the text OR href
                    # (This is a "catch-all" fallback)
                    fallback_link = container.find("a", href=lambda x: x and "/document/" in x)
                    
                    if fallback_link:
                        docs["annual_report_url"] = self.DOMAIN + fallback_link['href']
                        logger.info(f"      ✅ Found Annual Report (Fallback): {fallback_link.get_text(strip=True)}")                               


        # --- 3. Find GSP PDF (Submittal) ---
        # Look for links like "GSP 2020", "GSP 2022"
        gsp_link_text = soup.find("a", string=lambda t: t and "GSP" in t and "20" in t)
        
        if gsp_link_text and gsp_link_text.get('href'):
            # It's a link to another page (The 'GSP Plan Content' page)
            sub_page_url = self.DOMAIN + gsp_link_text['href']
            logger.info(f"      -> Follow-up: Checking GSP Sub-page: {sub_page_url}")

            try:
                # "Hop" to the next page
                await page.goto(sub_page_url, timeout=30000, wait_until="domcontentloaded")
                sub_content = await page.content()
                sub_soup = BeautifulSoup(sub_content, 'html.parser')
                
                # Look for "GSP Plan Content" section -> PDF
                # Sometimes it's under "Adopted GSP" or just a massive list. 
                # We grab the largest/main PDF usually listed first or explicitly named.
                
                # Strategy: Find any PDF link in the 'main' content area
                final_pdf = sub_soup.find("a", href=lambda x: x and x.lower().endswith(".pdf"))
                if final_pdf:
                    docs["gsp_url"] = self.DOMAIN + final_pdf['href']
                    logger.info(f"      ✅ Found GSP Document: {docs['gsp_url']}")
                    
            except Exception as e:
                logger.warning(f"      ⚠️ Could not resolve deep GSP link: {e}")

        return docs
    
# --- 🧪 Test Execution (Run this to verify) ---
if __name__ == "__main__":
    hunter = SGMADocumentHunter()
    
    # Test with Santa Cruz Mid-County (3-001)
    result = asyncio.run(hunter.get_basin_documents("5-022.08"))
    
    import json
    print(json.dumps(result, indent=2))