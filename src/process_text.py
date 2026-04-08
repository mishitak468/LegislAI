from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter


def clean_html(raw_html):
    """Strips HTML tags and returns clean text."""
    soup = BeautifulSoup(raw_html, "html.parser")
    # Get text and handle the <pre> tag specifically
    text = soup.get_text(separator="\n")
    return text.strip()


def chunk_bill(bill_data):
    """
    Takes the enriched bill dictionary and splits it into chunks with metadata.
    """
    text = clean_html(bill_data['full_text'])

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\nWhereas", "\nResolved", "\n\n", "\n", " "]
    )

    chunks = splitter.split_text(text)

    # We return a list of dictionaries with the text and the metadata
    # This is crucial for "FAANG-worthy" traceability
    return [
        {
            "text": chunk,
            "metadata": {
                "bill_number": bill_data['bill_number'],
                "title": bill_data['title'],
                "congress": bill_data['congress']
            }
        }
        for chunk in chunks
    ]


if __name__ == "__main__":
    import json
    # Quick test with your saved file
    with open("data/enriched_bills.json", "r") as f:
        data = json.load(f)
        if data:
            test_chunks = chunk_bill(data[0])
            print(f"Split bill into {len(test_chunks)} chunks.")
            print(f"First chunk preview:\n{test_chunks[0]['text'][:200]}...")
