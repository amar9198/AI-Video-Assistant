# 🎥 AI Video Assistant

An AI-powered application that helps users process video and audio content, convert speech into text, and make video content easier to understand. The application supports uploaded audio/video files and YouTube URLs, with speech transcription powered by Whisper and Sarvam AI.

## 🚀 Live Demo

**Try the application here:**

👉 [AI Video Assistant — Live App](https://ai-video-assistant-hmaeqbb2mtfrxli88xypjg.streamlit.app/)

## 📌 Project Overview

The AI Video Assistant is designed to simplify the process of understanding audio and video content using Artificial Intelligence.

Instead of manually watching an entire video and writing down its spoken content, users can provide a supported video, audio file, or YouTube URL. The application processes the audio, divides it into manageable chunks, and uses speech recognition models to generate a transcript for further analysis.

## ✨ Features

- 🎬 **Video and Audio Processing** — Process supported uploaded media files.
- 🔗 **YouTube URL Support** — Extract audio from supported YouTube videos.
- 🎙️ **Speech-to-Text Transcription** — Convert spoken content into text.
- 🤖 **AI-Powered Processing** — Use speech recognition models to process audio content.
- 🌐 **Multilingual Transcription Options** — Support English transcription with Whisper and a Sarvam AI transcription path for Hinglish.
- 🔊 **Audio Conversion** — Convert audio into mono, 16 kHz WAV format.
- ✂️ **Audio Chunking** — Divide longer audio into smaller segments for transcription.
- ☁️ **Web-Based Interface** — Access the application through Streamlit without installing a desktop application.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core application development |
| Streamlit | Web application interface |
| Groq API | Cloud-based Whisper transcription |
| Whisper | Speech recognition |
| Sarvam AI API | Hinglish transcription workflow |
| Pydub | Audio processing and chunking |
| FFmpeg | Audio/video conversion |
| yt-dlp | YouTube audio extraction |
| Requests | API communication |
| python-dotenv | Environment variable management |

## ⚙️ How It Works

1. **Input:** Provide a supported audio/video file or a YouTube URL.
2. **Audio Extraction:** Extract audio from the video or download audio from the supported YouTube source.
3. **Audio Conversion:** Convert the audio into mono, 16 kHz WAV format.
4. **Chunking:** Split the audio into smaller segments for processing.
5. **Transcription:** Send the audio segments to the selected speech recognition service.
6. **Text Output:** Combine the resulting transcript segments for downstream processing.

## 📂 Project Structure

```text
AI-Video-Assistant/
├── app.py
├── core/
│   └── transcriber.py
├── utils/
│   └── audio_processor.py
├── downloads/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

*Note: This is a representative structure based on the project's known files. Your repository may contain additional modules and folders.*

## 💻 Run the Project Locally

### 1. Clone the repository

Replace the placeholder below with your actual GitHub repository URL.

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd YOUR_PROJECT_FOLDER
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If the project requires FFmpeg, install it separately and ensure it is available in your system's PATH.

### 4. Configure environment variables

Create a `.env` file in the project root and add the API keys required by your chosen transcription services.

```env
GROQ_API_KEY=your_groq_api_key
GROQ_WHISPER_MODEL=whisper-large-v3-turbo
WHISPER_BACKEND=groq

SARVAM_API_KEY=your_sarvam_api_key
SARVAM_STT_MODEL=saaras:v2.5
```

Use real API keys in your local `.env` file. Do not commit this file or expose your secrets publicly. Sarvam credentials are needed for the Hinglish workflow; Groq credentials are needed for the Groq transcription workflow.

### 5. Start the application

```powershell
python -m streamlit run app.py
```

Open the local URL displayed in your terminal, usually:

```text
http://localhost:8501
```

## 🔑 API Requirements

- **Groq:** [Get a Groq API key](https://console.groq.com/keys)
- **Sarvam AI:** [Visit Sarvam AI](https://www.sarvam.ai/)

Configure the relevant credentials in your local `.env` file or your Streamlit deployment's secrets settings.

## ☁️ Deployment

The application is deployed using Streamlit Community Cloud.

**Live application:** [Open AI Video Assistant](https://ai-video-assistant-hmaeqbb2mtfrxli88xypjg.streamlit.app/)

## 🔮 Future Improvements

- Generate concise video summaries.
- Extract key points and important timestamps.
- Enable question answering based on video transcripts.
- Export transcripts and summaries as TXT or PDF files.
- Improve multilingual speech recognition.
- Add subtitle generation and speaker identification.
- Improve error handling and processing feedback for long videos.

## 👨‍💻 Author

**Amar Prajapati**

Explore my projects and connect with me on GitHub and LinkedIn.

## ⭐ Support

If you find this project useful, consider giving the repository a star on GitHub. Contributions, suggestions, and feedback are welcome.
