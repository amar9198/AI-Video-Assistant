from dotenv import load_dotenv
import concurrent.futures # <-- Add this import

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.rag_engine import build_rag_chain

load_dotenv()

def run_pipeline(source: str, language: str = "english", on_stage=None) -> dict:
    """Process a video or audio source and return its analysis."""

    def stage(number, label):
        if on_stage:
            on_stage(number, label)

    if not isinstance(source, str) or not source.strip():
        raise ValueError("Please provide a valid video URL or audio file path.")

    print("Starting AI Video Assistant")

    # Step 1: Download or prepare audio.
    stage(1, "Preparing audio")
    chunks = process_input(source)

    if not chunks:
        raise ValueError("No audio was extracted. Try another video or upload an audio file.")

    # Step 2: Transcribe audio.
    stage(2, "Transcribing audio")
    transcript = transcribe_all(chunks, language)

    if not isinstance(transcript, str):
        transcript = str(transcript or "")

    transcript = transcript.strip()
    print(f"Transcription length: {len(transcript)} characters")

    if len(transcript) < 20:
        raise ValueError(
            "Transcription returned too little text. "
            "Check the audio quality, transcription API, or selected language."
        )

    # Step 3: Generate title and summary.
    stage(3, "Generating title and summary")
    title = generate_title(transcript)
    summary = summarize(transcript)

    # Step 4: Extract structured information (Optimized for concurrency)
    stage(4, "Extracting action items, decisions and questions")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_actions = executor.submit(extract_action_items, transcript)
        future_decisions = executor.submit(extract_key_decisions, transcript)
        future_questions = executor.submit(extract_questions, transcript)
        
        action_items = future_actions.result()
        decisions = future_decisions.result()
        questions = future_questions.result()

    # Step 5: Build the question-answering chain.
    stage(5, "Preparing AI question-answering")
    rag_chain = build_rag_chain(transcript)

    return {
        "title": title or "Untitled",
        "transcript": transcript,
        "summary": summary or "",
        "action_items": action_items or "",
        "key_decisions": decisions or "",
        "open_questions": questions or "",
        "rag_chain": rag_chain,
    }