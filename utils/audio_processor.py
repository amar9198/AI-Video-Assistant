
import os
from pathlib import Path

import yt_dlp
from pydub import AudioSegment


# Use the project's root directory
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def download_youtube_audio(url: str) -> str:
    """Download YouTube audio and return the resulting WAV path."""

    output_template = str(DOWNLOAD_DIR / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "retries": 3,
        "fragment_retries": 3,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Prefer the actual path reported by yt-dlp
            filepath = info.get("filepath")

            if not filepath:
                original_path = Path(ydl.prepare_filename(info))
                filepath = str(original_path.with_suffix(".wav"))

        if not os.path.isfile(filepath):
            raise FileNotFoundError(
                f"Downloaded WAV file was not found: {filepath}"
            )

        return filepath

    except Exception as exc:
        raise RuntimeError(
            f"Could not download YouTube audio: {exc}"
        ) from exc


def convert_to_wav(input_path: str) -> str:
    """Convert audio/video to mono, 16 kHz WAV."""

    input_file = Path(input_path)

    if not input_file.is_file():
        raise FileNotFoundError(
            f"Input file not found: {input_path}"
        )

    output_path = input_file.with_name(
        f"{input_file.stem}_converted.wav"
    )

    audio = AudioSegment.from_file(str(input_file))
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(str(output_path), format="wav")

    return str(output_path)


def chunk_audio(
    wav_path: str,
    chunk_minutes: int = 10
) -> list[str]:
    """Split WAV audio into smaller WAV files."""

    if chunk_minutes <= 0:
        raise ValueError("chunk_minutes must be greater than zero.")

    audio = AudioSegment.from_wav(wav_path)

    if len(audio) == 0:
        raise ValueError("The audio file is empty.")

    chunk_ms = chunk_minutes * 60 * 1000
    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start:start + chunk_ms]

        chunk_path = str(
            Path(wav_path).with_suffix("")
        ) + f"_chunk_{i}.wav"

        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks


def process_input(source: str) -> list[str]:
    """Process either a YouTube URL or a local media file."""

    source = source.strip()

    if source.startswith(("http://", "https://")):
        print("Detected URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Using local media...")
        wav_path = source

    # Normalize both downloaded and uploaded media
    normalized_path = convert_to_wav(wav_path)

    print("Chunking audio...")
    chunks = chunk_audio(normalized_path)

    print(f"Audio ready — {len(chunks)} chunk(s) created.")

    return chunks
