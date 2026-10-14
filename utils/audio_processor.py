import os
import tempfile
import time
import yt_dlp
from pydub import AudioSegment

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


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
    """Optional YouTube cookies. Set YT_COOKIES_FILE=path, or YT_COOKIES
    (the full cookies.txt text) in .env / Streamlit secrets."""
    path = os.getenv("YT_COOKIES_FILE")
    if path and os.path.exists(path):
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
   
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "socket_timeout": 30,
        "retries": 3,

        # Explicitly enable Node.js for YouTube extraction
        "js_runtimes": {"node": {}},

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }

    cookies = _cookie_file()
    if cookies:
        ydl_opts["cookiefile"] = cookies

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    # after FFmpegExtractAudio the file is <id>.wav
    return os.path.join(DOWNLOAD_DIR, f"{info['id']}.wav")

def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000) #16khz
    audio.export(output_path, format="wav")
    return output_path



def chunk_audio(wav_path : str , chunk_minutes : int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000 

    chunks = []

    for i, start in enumerate(range(0,len(audio),chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path , format = "wav")

        chunks.append(chunk_path)
    
    return chunks

def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks