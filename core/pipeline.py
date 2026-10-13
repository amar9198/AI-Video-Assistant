from dotenv import load_dotenv
from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question  # noqa: F401  (ask_question re-exported)

load_dotenv()


def run_pipeline(source: str, language: str = "english", on_stage=None) -> dict:
    """Same pipeline as before. `on_stage(step, label)` is optional and only
    reports which real stage is starting (used by the Streamlit UI)."""
    def stage(n, label):
        if on_stage:
            on_stage(n, label)

    print("starting AI Video Assistant")

    stage(1, "Preparing audio")
    chunks = process_input(source)

    stage(2, "Transcribing audio")
    transcript = transcribe_all(chunks, language)
    print(f"raw transcription (first 300 characters ) {transcript[:300]}")

    stage(3, "Generating title and summary")
    title = generate_title(transcript)
    summary = summarize(transcript)

    stage(4, "Extracting action items, decisions and questions")
    action_item = extract_action_items(transcript)
    decisions = extract_key_decisions(transcript)
    questions = extract_questions(transcript)

    stage(5, "Preparing AI question-answering")
    rag_chain = build_rag_chain(transcript)

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_item,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }