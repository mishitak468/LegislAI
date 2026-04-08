import sys
import os

# This tells Python to look inside the 'src' folder for our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from vector_db import get_vector_store

print("Searching the database...")
db = get_vector_store()

query = "Who was Patrick Finucane?"
results = db.similarity_search(query, k=1)

if results:
    print("\n--- QUERY RESULT ---")
    print(results[0].page_content[:500] + "...")
    print("\n--- SOURCE METADATA ---")
    print(results[0].metadata)
else:
    print("No results found. Did you run load_to_db.py yet?")
