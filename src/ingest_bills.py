import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("CONGRESS_API_KEY")
BASE_URL = "https://api.congress.gov/v3/bill"


def fetch_recent_bills(limit=5):  # Reduced to 5 for testing
    params = {"api_key": API_KEY, "format": "json", "limit": limit}
    response = requests.get(BASE_URL, params=params)
    return response.json().get('bills', []) if response.status_code == 200 else []


def get_bill_text_url(congress, bill_type, bill_number):
    """Hits the /text endpoint to find the actual content URL."""
    url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type.lower()}/{bill_number}/text"
    params = {"api_key": API_KEY, "format": "json"}

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            versions = data.get("textVersions", [])
            if versions:
                # We take the latest version available
                formats = versions[-1].get("formats", [])
                for f in formats:
                    # We prefer 'Formatted Text' or 'Text' for cleaner chunking
                    if f.get("type") in ["Formatted Text", "Text", "XML"]:
                        return f.get("url")
    except Exception as e:
        print(f"Error finding text URL for {bill_number}: {e}")
    return None


def download_bill_content(text_url):
    """Downloads the raw text/HTML from the provided URL."""
    if not text_url:
        return ""
    params = {"api_key": API_KEY}
    response = requests.get(text_url, params=params)
    return response.text if response.status_code == 200 else ""

# def fetch_recent_bills(limit=50):
#     """Fetches the most recent bills from Congress.gov"""

#     headers = {
#         "x-api-key": API_KEY
#     }

#     # We want the most recent bills, format in JSON
#     params = {
#         "format": "json",
#         "limit": limit,
#         "offset": 0
#     }

#     print(f"Fetching {limit} recent bills from Congress.gov...")
#     response = requests.get(BASE_URL, headers=headers, params=params)

#     if response.status_code == 200:
#         data = response.json()

#         # Save to local data folder for exploration
#         output_path = os.path.join("data", "raw_bills.json")
#         os.makedirs("data", exist_ok=True)

#         with open(output_path, "w") as f:
#             json.dump(data, f, indent=4)

#         print(
#             f"Success! Saved {len(data.get('bills', []))} bills to {output_path}")
#         return data['bills']
#     else:
#         print(f"Failed to fetch data. Status code: {response.status_code}")
#         print(response.text)
#         return None


if __name__ == "__main__":
    if not API_KEY:
        print("Error: CONGRESS_API_KEY not found.")
    else:
        bills = fetch_recent_bills(limit=5)
        enriched_data = []

        for b in bills:
            print(f"Fetching text for: {b['type']}{b['number']}...")

            text_link = get_bill_text_url(
                b['congress'], b['type'], b['number'])
            full_text = download_bill_content(text_link)

            if full_text:
                enriched_data.append({
                    "congress": b['congress'],
                    "bill_type": b['type'],
                    "bill_number": b['number'],
                    "title": b['title'],
                    "full_text": full_text
                })
                print(f"Success!")
            else:
                print(f"No text found for {b['type']}{b['number']}")

        os.makedirs("data", exist_ok=True)
        with open("data/enriched_bills.json", "w") as f:
            json.dump(enriched_data, f, indent=4)

        print(
            f"\nDone! {len(enriched_data)} bills enriched and saved to data/enriched_bills.json")
