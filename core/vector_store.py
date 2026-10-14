
import os

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHROMA_DIR = "vector_db"
COLLECTION_NAME = "meeting_transcript"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
    )


def build_vector_store(transcript: str) -> Chroma:
    print("Building vector store...")

    # Validate transcript before creating embeddings.
    if not isinstance(transcript, str) or not transcript.strip():
        raise ValueError(
            "Cannot build vector store: the transcript is empty. "
            "Check the transcription output."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    chunks = [
        chunk.strip()
        for chunk in splitter.split_text(transcript)
        if chunk.strip()
    ]

    # Never send an empty document list to ChromaDB.
    if not chunks:
        raise ValueError(
            "Cannot build vector store: no text chunks were generated."
        )

    docs = [
        Document(
            page_content=chunk,
            metadata={"chunk_index": i},
        )
        for i, chunk in enumerate(chunks)
    ]

    print(f"Creating embeddings for {len(docs)} text chunks...")

    embeddings = get_embeddings()

    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
    )

    print("Vector store created successfully.")
    return vector_store


def load_vector_store() -> Chroma:
    embeddings = get_embeddings()

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )


def get_retriever(vector_store: Chroma, k: int = 4):
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )
