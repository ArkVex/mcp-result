from typing import Any, Optional, List, Dict
import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
import json
import time
from dataclasses import dataclass

mcp = FastMCP("dsce_results_scraper")

@dataclass
class StudentResult:
    usn: str
    name: Optional[str]
    semester: Optional[str]
    results: Dict[str, Any]

class DsceScraper:
    def __init__(self):
        self.base_url = "https://www.dsce.edu.in/results"
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.results_cache = {}

    def generate_usns(self, year: str, branch: str, start: int = 1, end: int = 300) -> List[str]:
        """Generate USNs based on the pattern 1DSxxBRxxx"""
        usns = []
        for num in range(start, end + 1):
            usn = f"1DS{year}{branch}{num:03d}"
            usns.append(usn)
        return usns

    def scrape_result(self, usn: str) -> Optional[StudentResult]:
        """Scrape result for a single USN"""
        if usn in self.results_cache:
            return self.results_cache[usn]

        try:
            # Add delay to avoid overwhelming the server
            time.sleep(1.5)

            # Make POST request to fetch results
            data = {
                "usn": usn,
                "submit": "Get Result"
            }
            response = self.session.post(self.base_url, data=data, headers=self.headers)
            response.raise_for_status()

            # Parse the response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Initialize variables
            name = None
            semester = None
            results = {}

            # Try to find student details
            student_info = soup.find_all('table')
            for table in student_info:
                text = table.get_text().lower()
                if 'name' in text:
                    # Try to extract name
                    name_row = table.find('tr')
                    if name_row:
                        name = name_row.find_all('td')[-1].text.strip()
                if 'semester' in text:
                    # Try to extract semester
                    sem_row = table.find('tr')
                    if sem_row:
                        semester = sem_row.find_all('td')[-1].text.strip()

            # Find results table - usually the last table on the page
            tables = soup.find_all('table')
            if tables:
                results_table = tables[-1]  # Usually the last table contains results
                for row in results_table.find_all('tr')[1:]:  # Skip header row
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        subject = cols[0].text.strip()
                        # Combine all remaining columns into the result
                        result_data = {
                            "marks": cols[1].text.strip() if len(cols) > 1 else "N/A",
                            "grade": cols[2].text.strip() if len(cols) > 2 else "N/A",
                            "status": cols[3].text.strip() if len(cols) > 3 else "N/A"
                        }
                        results[subject] = result_data

            # Only cache and return if we found some results
            if results:
                result = StudentResult(usn=usn, name=name, semester=semester, results=results)
                self.results_cache[usn] = result
                return result
            return None

        except Exception as e:
            print(f"Error scraping results for USN {usn}: {str(e)}")
            return None

scraper = DsceScraper()

@mcp.tool()
async def scrape_batch_results(year: str, branch: str, start_num: int = 1, end_num: int = 300) -> str:
    """
    Scrape results for a batch of students based on year and branch.
    
    Args:
        year: Year (e.g., "22", "23")
        branch: Branch code (e.g., "IS", "CS", "IOT")
        start_num: Starting USN number (default: 1)
        end_num: Ending USN number (default: 300)
    """
    try:
        usns = scraper.generate_usns(year, branch, start_num, end_num)
        results = []
        total = len(usns)
        
        print(f"Starting to scrape {total} USNs...")
        
        for i, usn in enumerate(usns, 1):
            print(f"Processing {i}/{total}: {usn}")
            result = scraper.scrape_result(usn)
            if result:
                results.append({
                    "usn": result.usn,
                    "name": result.name,
                    "semester": result.semester,
                    "results": result.results
                })
                print(f"Found results for {usn}")
            else:
                print(f"No results found for {usn}")
        
        if results:
            return json.dumps(results, indent=2)
        return "No results found for any USN in the given range"
    except Exception as e:
        return f"Error scraping results: {str(e)}"

@mcp.tool()
async def get_single_result(usn: str) -> str:
    """
    Get result for a single USN.
    
    Args:
        usn: Complete USN (e.g., "1DS22IS028")
    """
    try:
        print(f"Fetching results for {usn}...")
        result = scraper.scrape_result(usn)
        if result:
            return json.dumps({
                "usn": result.usn,
                "name": result.name,
                "semester": result.semester,
                "results": result.results
            }, indent=2)
        return f"No results found for USN: {usn}"
    except Exception as e:
        return f"Error fetching result: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio') 