from typing import Any, Optional, List, Dict
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json
import time
from dataclasses import dataclass

@dataclass
class StudentResult:
    usn: str
    name: Optional[str]
    semester: Optional[str]
    results: Dict[str, Any]

class DsceScraper:
    def __init__(self):
        self.base_url = "https://www.dsce.edu.in/results"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.dsce.edu.in',
            'DNT': '1',
            'Connection': 'keep-alive'
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
            time.sleep(2)

            # Prepare the POST data
            data = urllib.parse.urlencode({
                "usn": usn,
                "submit": "Get Result"
            }).encode('utf-8')

            print(f"\nFetching {usn}...")
            
            # Create request object
            req = urllib.request.Request(
                self.base_url,
                data=data,
                headers=self.headers,
                method='POST'
            )

            # Make the request
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                print(f"Response status: {response.status}")

                # Save the response for debugging
                with open(f"debug_{usn}.html", "w", encoding="utf-8") as f:
                    f.write(html)

                # Parse the response
                soup = BeautifulSoup(html, 'html.parser')
                
                # Initialize variables
                name = None
                semester = None
                results = {}

                # Try to find student details in any table
                tables = soup.find_all('table')
                print(f"Found {len(tables)} tables on the page")

                for table in tables:
                    text = table.get_text().lower()
                    rows = table.find_all('tr')
                    
                    # Look for student details
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            header = cells[0].text.strip().lower()
                            if 'name' in header and not name:
                                name = cells[1].text.strip()
                                print(f"Found name: {name}")
                            elif 'semester' in header and not semester:
                                semester = cells[1].text.strip()
                                print(f"Found semester: {semester}")

                    # Look for results
                    headers = [th.text.strip().lower() for th in table.find_all('th')]
                    if any(keyword in ' '.join(headers) for keyword in ['subject', 'marks', 'grade']):
                        print("\nFound possible results table")
                        for row in table.find_all('tr')[1:]:  # Skip header row
                            cols = row.find_all('td')
                            if len(cols) >= 2:
                                subject = cols[0].text.strip()
                                result_data = {
                                    "marks": cols[1].text.strip() if len(cols) > 1 else "N/A",
                                    "grade": cols[2].text.strip() if len(cols) > 2 else "N/A",
                                    "status": cols[3].text.strip() if len(cols) > 3 else "N/A"
                                }
                                results[subject] = result_data
                                print(f"Found result for {subject}")

                # Only cache and return if we found some results
                if results:
                    result = StudentResult(usn=usn, name=name, semester=semester, results=results)
                    self.results_cache[usn] = result
                    return result
                
                print("No results found in any table")
                return None

        except Exception as e:
            print(f"Error scraping results for USN {usn}: {str(e)}")
            return None

def scrape_batch_results(year: str, branch: str, start_num: int = 1, end_num: int = 300):
    """
    Scrape results for a batch of students based on year and branch.
    """
    scraper = DsceScraper()
    try:
        usns = scraper.generate_usns(year, branch, start_num, end_num)
        results = []
        total = len(usns)
        
        print(f"Starting to scrape {total} USNs...")
        
        for i, usn in enumerate(usns, 1):
            print(f"\nProcessing {i}/{total}: {usn}")
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
            # Save results to a JSON file
            filename = f"results_{year}_{branch}_{start_num}_{end_num}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to {filename}")
            return results
        print("\nNo results found for any USN in the given range")
        return None
    except Exception as e:
        print(f"Error scraping results: {str(e)}")
        return None

def get_single_result(usn: str):
    """
    Get result for a single USN.
    """
    scraper = DsceScraper()
    try:
        print(f"Fetching results for {usn}...")
        result = scraper.scrape_result(usn)
        if result:
            # Save result to a JSON file
            filename = f"result_{usn}.json"
            with open(filename, 'w') as f:
                json.dump({
                    "usn": result.usn,
                    "name": result.name,
                    "semester": result.semester,
                    "results": result.results
                }, f, indent=2)
            print(f"\nResult saved to {filename}")
            return result
        print(f"\nNo results found for USN: {usn}")
        return None
    except Exception as e:
        print(f"Error fetching result: {str(e)}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("1. For single USN: python scraper.py single 1DS22IS028")
        print("2. For batch: python scraper.py batch 22 IS [start_num] [end_num]")
        sys.exit(1)

    mode = sys.argv[1].lower()
    
    if mode == "single":
        if len(sys.argv) != 3:
            print("For single USN mode, provide the USN")
            print("Example: python scraper.py single 1DS22IS028")
            sys.exit(1)
        get_single_result(sys.argv[2])
    
    elif mode == "batch":
        if len(sys.argv) < 4:
            print("For batch mode, provide at least year and branch")
            print("Example: python scraper.py batch 22 IS [start_num] [end_num]")
            sys.exit(1)
            
        year = sys.argv[2]
        branch = sys.argv[3]
        start_num = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        end_num = int(sys.argv[5]) if len(sys.argv) > 5 else 300
        
        scrape_batch_results(year, branch, start_num, end_num)
    
    else:
        print("Invalid mode. Use 'single' or 'batch'")
        sys.exit(1) 