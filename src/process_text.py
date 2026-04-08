from langchain.text_splitter import RecursiveCharacterTextSplitter


def split_bill_text(text, chunk_size=1000, chunk_overlap=150):
    """
    Splits long legal text into overlapping chunks.
    Overlap ensures that context (like 'Section 5') isn't lost at the edges.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_text(text)
