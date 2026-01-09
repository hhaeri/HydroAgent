# 💧 HydroAgent

**An autonomous AI agent for accessing and analyzing California Groundwater Data.**

HydroAgent is a specialized tool designed to navigate the [California DWR SGMA Portal](https://sgma.water.ca.gov/portal/), locating critical groundwater sustainability documents (Annual Reports and GSPs) that are often buried behind complex web interfaces. It automates the "hunt" for data, enabling downstream RAG (Retrieval-Augmented Generation) systems to answer questions about aquifer health, storage changes, and sustainability goals.

## 🚀 Features

* **Intelligent Navigation:** Uses `Playwright` to autonomously navigate the SGMA portal, handling dynamic tables, search filters, and pagination like a human researcher.
* **Dynamic Mapping:** Automatically maps table columns (e.g., "Basin Name", "Year") to adapt to layout changes on the government website.
* **Smart Harvesting:** Identifies the correct PDF reports using robust pattern matching (e.g., `WY_2024`) rather than relying on brittle HTML IDs.
* **Resilience:** Built with advanced error handling and "wait-for-content" strategies to handle slow-loading government servers without crashing.

## 📂 Project Structure

```text
HydroAgent/
├── modules/
│   ├── document_hunter.py  # The core web-scraping agent
│   └── (future modules)    # Reader, Analyzer, etc.
├── docs/
│   └── document_hunter.md  # Detailed technical documentation
├── .venv/                  # Virtual environment
├── requirements.txt        # Python dependencies
└── main.py                 # Entry point (Coming soon)
```

## 🛠️ Installation & Setup

Prerequisites
Python 3.10+

VS Code (Recommended)

1. Clone & Install

```python
git clone [https://github.com/yourusername/HydroAgent.git](https://github.com/yourusername/HydroAgent.git)
cd HydroAgent

# Create virtual environment
python -m venv .venv

# Activate it
# Mac/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```
2. Install Browsers (Critical)
HydroAgent uses Playwright, which requires its own browser binaries.

```python
playwright install
```
## 🏃 Usage
Currently, the document_hunter module can be run directly to test the scraping logic.

```python
import asyncio
from modules.document_hunter import SGMADocumentHunter

async def main():
    hunter = SGMADocumentHunter()
    # Search for Santa Cruz Mid-County Basin (3-001)
    results = await hunter.get_basin_documents("3-001")
    print(results)

if __name__ == "__main__":
    asyncio.run(main())
```
## 🗺️ Roadmap
[x] Module 1: Document Hunter (Locate & Extract URLs)

[ ] Module 2: The Reader (Download & Parse PDFs into Markdown)

[ ] Module 3: The Analyst (RAG-based QA using LLMs)

[ ] Web Interface (Simple Streamlit UI)

## 🤝 Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements to the scraping logic or new features.

## 📄 License
MIT License [https://www.google.com/search?q=LICENSE]
