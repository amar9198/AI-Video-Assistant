
import os
import tempfile
import time
import shutil
import yt_dlp
from pydub import AudioSegment
import subprocess
from pathlib import Path

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)




def ensure_deno() -> str:
    """Find Deno or install it if it is missing."""
    deno_path = shutil.which("deno")

    # Deno is already available
    if deno_path:
        print("Deno found:", deno_path)
        return deno_path

    # Define the installation path before using it
    install_dir = Path.home() / ".deno"
    deno_path = install_dir / "bin" / "deno"

    # Install Deno
    env = os.environ.copy()
    env["DENO_INSTALL"] = str(install_dir)

    try:
        subprocess.run(
            ["sh", "-c", "curl -fsSL https://deno.land/install.sh | sh"],
            check=True,
            timeout=180,
            env=env,
        )
    except Exception as exc:
        raise RuntimeError(f"Deno installation failed: {exc}") from exc

    if not deno_path.is_file():
        raise RuntimeError(
            f"Deno was not installed at {deno_path}. "
            "Check the deployment logs."
        )

    print("Deno installed:", deno_path)
    return str(deno_path)




def _cleanup_old_files(max_age_hours: int = 2) -> None:
    cutoff = time.time() - max_age_hours * 3600

    for name in os.listdir(DOWNLOAD_DIR):
        path = os.path.join(DOWNLOAD_DIR, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def _cookie_file():
    """Get optional YouTube cookies from environment variables."""
    path = os.getenv("YT_COOKIES_FILE")
    if path and os.path.isfile(path):
        return path

    content = os.getenv("YT_COOKIES")
    if content:
        tmp = os.path.join(tempfile.gettempdir(), "yt_cookies.txt")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        return tmp

    return None




def download_youtube_audio(url: str) -> str:
    _cleanup_old_files()

    print("yt-dlp version:", yt_dlp.version.__version__)

    ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
    "noplaylist": True,
    "retries": 3,
    "fragment_retries": 3,
    "js_runtimes": {
        "deno": {
            "path": deno_path
        }
    },
    "remote_components": {
        "ejs:npm"
    },
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
        }
    ],
}

    deno_path = ensure_deno()

    ydl_opts["js_runtimes"] = {
    "deno": {"path": deno_path}
}
    ydl_opts["remote_components"] = {"ejs:npm"}

    cookies = _cookie_file()
    if cookies:
        ydl_opts["cookiefile"] = cookies
        print("Using configured YouTube cookies.")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info:
            raise RuntimeError("yt-dlp returned no video information.")

        wav_path = os.path.join(DOWNLOAD_DIR, f"{info['id']}.wav")

        if not os.path.isfile(wav_path):
            raise FileNotFoundError(
                f"Downloaded WAV file was not found: {wav_path}"
            )

        if os.path.getsize(wav_path) == 0:
            raise ValueError("The downloaded WAV file is empty.")

        return wav_path

    except Exception as e:
        print(f"YouTube download failed: {type(e).__name__}: {e}")
        raise RuntimeError(
            "Could not download YouTube audio. "
            "Try another public video or upload the media directly. "
            f"Details: {type(e).__name__}: {e}"
        ) from e



def convert_to_wav(input_path: str) -> str:
    """Convert an audio/video file to mono, 16 kHz WAV."""
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = os.path.splitext(input_path)[0] + "_converted.wav"

    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")

    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    """Split WAV audio into chunks for transcription."""
    if chunk_minutes <= 0:
        raise ValueError("chunk_minutes must be greater than zero.")

    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000
    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start:start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    if not chunks:
        raise ValueError("No audio chunks were created.")

    return chunks


def process_input(source: str) -> list:
    source = source.strip()

    if not source:
        raise ValueError("Please provide a YouTube URL or audio/video file.")

    if source.startswith(("http://", "https://")):
        print("Detected URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")

    return chunks
