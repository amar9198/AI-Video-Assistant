
import os
import requests
from dotenv import load_dotenv
from pydub import AudioSegment
from groq import Groq

load_dotenv()

GROQ_WHISPER_MODEL = os.getenv(
    "GROQ_WHISPER_MODEL", "whisper-large-v3-turbo"
)
WHISPER_BACKEND = os.getenv("WHISPER_BACKEND", "groq").lower()
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

SARVAM_PIECE_SECONDS = 25
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_STT_TRANSLATE_URL = (
    "https://api.sarvam.ai/speech-to-text-translate"
)
SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v2.5")

_model = None


def load_model():
    global _model

    if _model is None:
        import whisper

        print(f"Loading local Whisper model: {WHISPER_MODEL} ...")
        _model = whisper.load_model(WHISPER_MODEL)
        print("Local Whisper model loaded.")

    return _model


def transcribe_chunk_whisper(chunk_path: str) -> str:
    if WHISPER_BACKEND == "local":
        result = load_model().transcribe(
            chunk_path,
            task="transcribe",
        )
        text = result.get("text", "")
    else:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set in Streamlit secrets or .env."
            )

        client = Groq(api_key=api_key, timeout=120)

        with open(chunk_path, "rb") as f:
            result = client.audio.transcriptions.create(
                file=(os.path.basename(chunk_path), f.read()),
                model=GROQ_WHISPER_MODEL,
                language="en",
            )

        text = result.text or ""

    if not text.strip():
        raise ValueError(
            f"Transcription returned empty text for {chunk_path}."
        )

    return text.strip()


def _send_to_sarvam(piece_path: str) -> str:
    if not SARVAM_API_KEY:
        raise RuntimeError(
            "SARVAM_API_KEY is not set in Streamlit secrets or .env."
        )

    headers = {"api-subscription-key": SARVAM_API_KEY}

    with open(piece_path, "rb") as f:
        files = {
            "file": (os.path.basename(piece_path), f, "audio/wav")
        }
        data = {
            "model": SARVAM_MODEL,
            "with_diarization": "false",
        }
        response = requests.post(
            SARVAM_STT_TRANSLATE_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

    if not response.ok:
        print(f"Sarvam returned {response.status_code}: {response.text}")
        response.raise_for_status()

    text = response.json().get("transcript", "")
    if not text.strip():
        raise ValueError(
            f"Sarvam returned an empty transcript for {piece_path}."
        )

    return text.strip()


def transcribe_chunk_sarvam(chunk_path: str) -> str:
    if not SARVAM_API_KEY:
        raise RuntimeError(
            "SARVAM_API_KEY is not set in Streamlit secrets or .env."
        )

    audio = AudioSegment.from_wav(chunk_path)
    piece_ms = SARVAM_PIECE_SECONDS * 1000
    pieces = []

    total_pieces = (len(audio) + piece_ms - 1) // piece_ms

    for i, start in enumerate(range(0, len(audio), piece_ms)):
        piece = audio[start : start + piece_ms]
        piece_path = f"{chunk_path}_sv_{i}.wav"
        piece.export(piece_path, format="wav")

        try:
            print(f"Sarvam piece {i + 1}/{total_pieces} ...")
            pieces.append(_send_to_sarvam(piece_path))
        finally:
            if os.path.exists(piece_path):
                os.remove(piece_path)

    transcript = " ".join(text for text in pieces if text).strip()

    if not transcript:
        raise ValueError("Sarvam returned an empty transcript.")

    return transcript


def transcribe_chunk(
    chunk_path: str,
    language: str = "english",
) -> str:
    if language.lower() == "hinglish":
        return transcribe_chunk_sarvam(chunk_path)

    return transcribe_chunk_whisper(chunk_path)


def transcribe_all(chunks: list, language: str = "english") -> str:
    if not chunks:
        raise ValueError("No audio chunks were provided for transcription.")

    engine = (
        "Sarvam AI"
        if language.lower() == "hinglish"
        else f"Whisper ({WHISPER_BACKEND})"
    )
    print(f"Using {engine} for transcription.")

    transcripts = []

    for i, chunk in enumerate(chunks):
        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")
        text = transcribe_chunk(chunk, language=language)

        if text and text.strip():
            transcripts.append(text.strip())

    full_transcript = " ".join(transcripts).strip()

    if not full_transcript:
        raise ValueError(
            "Transcription completed without producing any text."
        )

    print(f"Transcription complete ({len(full_transcript)} characters).")
    return full_transcript
