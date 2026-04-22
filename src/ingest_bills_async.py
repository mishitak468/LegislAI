import asyncio
import aiohttp
import json
import os
import logging
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

load_dotenv()
API_KEY = os.getenv("CONGRESS_API_KEY")

# Setup Logging
logging.basicConfig(level=logging.INFO, filename='logs/pipeline.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')


async def fetch_bill_text(session, bill):
    """Asynchronously fetches the full text link and content for a bill."""
    congress = bill['congress']
    b_type = bill['type'].lower()
    b_num = bill['number']

    url = f"https://api.congress.gov/v3/bill/{congress}/{b_type}/{b_num}/text"
    try:
        async with session.get(url, params={"api_key": API_KEY, "format": "json"}) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                text_urls = data.get('textVersions', [])
                if text_urls:
                    # Target the first available XML or HTML format
                    content_url = text_urls[0]['formats'][0]['url']
                    async with session.get(content_url) as text_resp:
                        if text_resp.status == 200:
                            text = await text_resp.text()
                            return {
                                "congress": congress,
                                "bill_number": str(b_num),
                                "title": bill['title'],
                                "full_text": text
                            }
    except Exception as e:
        logging.error(f"Failed to fetch {b_type}{b_num}: {e}")
    return None


async def main():
    # Adding 'format=json' directly into the URL string can sometimes override stubborn defaults
    list_url = "https://api.congress.gov/v3/bill/118?format=json"

    async with aiohttp.ClientSession() as session:
        async with session.get(list_url, params={"api_key": API_KEY, "limit": 50}) as resp:
            raw_text = await resp.text()

            try:
                data = json.loads(raw_text)
                bills = data.get('bills', [])
            except json.JSONDecodeError:
                logging.error(
                    f"API returned non-JSON content: {raw_text[:200]}")
                print(
                    "❌ The API returned XML or an error instead of JSON. Check logs/pipeline.log")
                return

        tasks = [fetch_bill_text(session, b) for b in bills]
        results = await tqdm.gather(*tasks, desc="Async Ingesting Bills")

        enriched = [r for r in results if r]
        with open("data/enriched_bills.json", "w") as f:
            json.dump(enriched, f, indent=4)
        print(f"✅ Success! {len(enriched)} bills saved.")

if __name__ == "__main__":
    asyncio.run(main())
