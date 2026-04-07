import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("CONGRESS_API_KEY")
BASE_URL = "https://api.congress.gov/v3/bill"


def fetch_recent_bills(limit=50):
    """Fetches the most recent bills from Congress.gov"""

    headers = {
        "x-api-key": API_KEY
    }

    # We want the most recent bills, format in JSON
    params = {
        "format": "json",
        "limit": limit,
        "offset": 0
    }

    print(f"Fetching {limit} recent bills from Congress.gov...")
    response = requests.get(BASE_URL, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()

        # Save to local data folder for exploration
        output_path = os.path.join("data", "raw_bills.json")
        os.makedirs("data", exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(data, f, indent=4)

        print(
            f"Success! Saved {len(data.get('bills', []))} bills to {output_path}")
        return data['bills']
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        print(response.text)
        return None


if __name__ == "__main__":
    if not API_KEY:
        print("Error: CONGRESS_API_KEY not found in environment.")
    else:
        bills = fetch_recent_bills()
        if bills:
            # Print a quick preview of the first bill to understand the structure
            print("\nPreview of the first bill retrieved:")
            print(f"Title: {bills[0].get('title')}")
            print(
                f"Type: {bills[0].get('type')} - Number: {bills[0].get('number')}")
            print(
                f"Latest Action: {bills[0].get('latestAction', {}).get('text')}")
