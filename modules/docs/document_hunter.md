# 🕵️ Module: Document Hunter

**File**: `modules/document_hunter.py `

**Status**: Production Ready 

**Dependencies**: `playwright`, `beautifulsoup4`, `asyncio`

# 1. Overview
The **Document Hunter** is an intelligent web-scraping agent designed to navigate the **California DWR SGMA Portal**. Unlike standard scrapers that break when website layouts change, this module uses "human-like" reasoning to locate, filter, and extract critical groundwater reports (Annual Reports and Groundwater Sustainability Plans).

**Key Capabilities**
* **Dynamic Column Mapping**: It reads the table headers to understand which column is "Basin Name" or "Year," making it resilient to layout changes.
* **Search Filter Interaction**: Instead of clicking "Next Page" 100 times, it types into the portal's search box and waits for the table to update.
* **Pattern-Based Extraction**: It identifies reports by analyzing file naming conventions (e.g., WY_2024) rather than relying on unstable HTML IDs.
* **Timeout Resilience**: Uses domcontentloaded strategies to prevent crashes on slow government servers.

# 2. Architecture & Logic
The module consists of a single class `SGMADocumentHunter` with three primary stages of execution:

**Stage 1: The Scout** (`_find_basin_page`)
1. Navigates to the "Submitted Annual Reports" page.
2. Maps Headers: Scans `<thead>` to find indices for "Basin" and "Report Year".
3. Filters: Types the Basin ID (e.g., "3-001") into the search box.
4. Selects: Identifies the row with the latest year (e.g., 2024) and extracts the link to the Basin Details Page.

**Stage 2: The Harvester** (_harvest_pdfs)
1. Navigates to the specific Basin Details Page found in Stage 1.
2. Pattern Match: Searches for a download link where the visible text contains `WY_{Year}` (e.g., `WY_2024`). This avoids downloading the wrong file or getting stuck on database IDs.
3. Fallback: If the pattern fails, it looks for the "Annual Report PDF" header and grabs the nearest PDF link.
4. GSP Lookup: Identifies links to the "Groundwater Sustainability Plan" (GSP) for context.

# 3. Class Reference
`class SGMADocumentHunter`

**Main Method**
```python
async def get_basin_documents(self, basin_identifier: str) -> Dict[str, Union[str, int, None]]
```
* **Purpose**: The main entry point for the agent. Orchestrates the finding and harvesting process.

* **Arguments**:

  * `basin_identifier` (str): The search term. Can be a Basin Code (e.g., `"3-001"`) or Name (e.g., `"Santa Cruz"`).

* **Returns**: A dictionary containing:

  * `basin_name`: The full official name found in the table.

  * `latest_year`: The year of the most recent report found.

  * `annual_report_url`: Direct URL to the PDF.

  * `gsp_url`: Direct URL to the GSP document (or sub-page).

Internal Helper Methods
* `_find_basin_page(page, identifier)`: Handles table interaction, filtering, and dynamic header mapping.

* `_harvest_pdfs(page, url, year)`: Scrapes the final PDF links using text pattern matching.

# 4. Usage Example
Here is how to call this tool from your main agent script or `main.py`.

```python
import asyncio
from modules.document_hunter import SGMADocumentHunter

async def main():
    # 1. Initialize the Hunter
    hunter = SGMADocumentHunter()
    
    # 2. Define your target (Name or Code works)
    target = "3-001" 
    
    print(f"🤖 Agent: Hunting for documents regarding '{target}'...")
    
    # 3. Execute (must be awaited)
    results = await hunter.get_basin_documents(target)
    
    # 4. Handle Results
    if results:
        print(f"✅ Found Report for: {results['basin_name']}")
        print(f"📅 Year: {results['latest_year']}")
        print(f"📄 Annual Report URL: {results['annual_report_url']}")
        print(f"📘 GSP URL: {results['gsp_url']}")
    else:
        print("❌ No documents found.")

if __name__ == "__main__":
    asyncio.run(main())
```
    
# 5. Troubleshooting & FAQ
Q: I get a `TimeoutError` waiting for the page to load.

Reason: The DWR website often has slow-loading maps or analytics scripts.

Fix: The code uses `wait_until="domcontentloaded"`. If errors persist, check your internet connection or increase the `timeout=60000` (60s) in `_harvest_pdfs`.

Q: The agent finds the basin but says "No Annual Report found".

Reason: The basin might use a non-standard naming convention for its PDF.

Fix: Check the logs. The agent tries a "Pattern Match" (`WY_2024`) first, then a "Header Match". If both fail, inspect the specific page manually to see if the PDF link is hidden behind a JavaScript button (which might require a code update).

Q: ModuleNotFoundError: No module named 'playwright'

Fix: Ensure you are in the correct `venv` and have installed the browsers:

```python
pip install playwright
playwright install
```
