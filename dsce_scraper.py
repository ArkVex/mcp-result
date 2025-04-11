import sys
import os
import json
import logging
import asyncio
import aiohttp
from pathlib import Path
import traceback
from typing import Any
from mcp.server.fastmcp import FastMCP

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# List of branch codes
BRANCH_CODES = [
    "AE", "AI", "AU", "BT", "CB", "CD", "CG", "CH", "CS",
    "CV", "CY", "EC", "EE", "EI", "ET", "IC", "IS", "MD",
    "ME", "RI"
]

class DsceResultScraper:
    def __init__(self):
        self.base_url = os.getenv('USN_URL', 'http://14.99.184.178:8080/birt/frameset')
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/pdf'
        }
        self.session = None

    async def init_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_pdf(self, usn: str, output_dir: str = "results") -> dict:
        try:
            await self.init_session()
            os.makedirs(output_dir, exist_ok=True)
            
            # Construct the URL with the correct parameters
            params = {
                '__report': 'mydsi/exam/Exam_Result_Sheet_dsce.rptdesign',
                '__format': 'pdf',
                'USN': usn.upper()
            }
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch PDF for {usn}. Status: {response.status}")
                    return {
                        "success": False,
                        "message": f"Failed to fetch PDF for {usn}. Status code: {response.status}"
                    }

                output_path = os.path.join(output_dir, f"{usn}.pdf")
                content = await response.read()
                with open(output_path, 'wb') as f:
                    f.write(content)
                logger.info(f"Saved PDF for {usn} to {output_path}")

                return {
                    "success": True,
                    "message": f"Successfully saved PDF for {usn}",
                    "path": output_path
                }

        except Exception as e:
            logger.error(f"Error fetching PDF for {usn}: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    async def fetch_branch(self, year: str, branch_code: str, output_dir: str = "results") -> dict:
        try:
            branch_dir = os.path.join(output_dir, branch_code.upper())
            os.makedirs(branch_dir, exist_ok=True)

            results = []
            consecutive_failures = 0
            student_number = 1
            max_consecutive_failures = 10

            logger.info(f"Fetching results for branch {branch_code}, year {year}")
            while consecutive_failures < max_consecutive_failures:
                usn = f"1DS{year}{branch_code.upper()}{str(student_number).zfill(3)}"
                result = await self.fetch_pdf(usn, branch_dir)

                if not result["success"]:
                    consecutive_failures += 1
                    logger.debug(f"Failure #{consecutive_failures} for {usn}")
                else:
                    consecutive_failures = 0
                    results.append(result)

                student_number += 1
                await asyncio.sleep(0.1)  # Rate limiting

            return {
                "success": True,
                "total": len(results),
                "results": results
            }

        except Exception as e:
            logger.error(f"Error processing branch {branch_code}: {str(e)}")
            return {
                "success": False,
                "message": f"Error processing branch: {str(e)}"
            }

# Initialize FastMCP and scraper
mcp = FastMCP("dsce_results_scraper")
scraper = DsceResultScraper()

@mcp.tool()
async def fetch_single_result(usn: str, output_dir: str = "results") -> dict:
    """Fetch a single result PDF by USN.

    Args:
        usn: The USN to fetch results for
        output_dir: Directory to save the PDF (default: results)
    """
    return await scraper.fetch_pdf(usn, output_dir)

@mcp.tool()
async def fetch_branch_results(year: str, branch_code: str, output_dir: str = "results") -> dict:
    """Fetch results for an entire branch.

    Args:
        year: The year code (e.g., "19" for 2019)
        branch_code: The branch code (e.g., "CS" for Computer Science)
        output_dir: Directory to save PDFs (default: results)
    """
    return await scraper.fetch_branch(year, branch_code, output_dir)

@mcp.tool()
async def get_branch_codes() -> list[str]:
    """Get the list of available branch codes."""
    return BRANCH_CODES

if __name__ == "__main__":
    try:
        # Always use ProactorEventLoop on Windows
        if sys.platform == 'win32':
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            logger.debug("Set Windows event loop to ProactorEventLoop")
        
        # Run the MCP server
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error in server: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)
    finally:
        try:
            loop = asyncio.get_event_loop()
            loop.close()
            logger.debug("Closed event loop")
        except Exception as e:
            logger.error(f"Error closing event loop: {e}")
