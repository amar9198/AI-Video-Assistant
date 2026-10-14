import html

import json

import os

import re

import shutil

import sqlite3

import tempfile

import uuid

from datetime import datetime

from pathlib import Path



import streamlit as st

from dotenv import load_dotenv



load_dotenv()



APP_NAME, APP_VERSION = "AI Video Assistant", "1.0.0"

DB_PATH = Path(__file__).parent / "data" / "history.db"

ALLOWED_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

YT_RE = re.compile(r"^(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/|live/)|youtu\.be/)[\w-]{6,}", re.I)

ENGINES = {"English": ("english", "Whisper"), "Hinglish": ("hinglish", "Sarvam AI")}

SUGGESTED = ["Summarize the main topic.", "What are the most important decisions?",

             "What actions should be taken next?", "Explain the most important concepts."]

PAGES = ["Dashboard", "New Analysis", "My Analysis", "Settings / About"]



st.set_page_config(page_title=APP_NAME, page_icon="🎬", layout="wide")



st.markdown("""<style>

.block-container{max-width:1150px;padding-top:2rem}

.hero h1{font-size:clamp(1.8rem,4vw,2.8rem);line-height:1.15;margin:0 0 .5rem}

.hero p{color:#9aa4c7;font-size:1.05rem;max-width:640px}

.accent{background:linear-gradient(90deg,#7c83ff,#b18cff);-webkit-background-clip:text;color:transparent}

.card{background:#121a30;border:1px solid #232c4a;border-radius:16px;padding:1.1rem 1.2rem;height:100%}

.card h4{margin:.2rem 0 .3rem;font-size:1rem}.card p{color:#9aa4c7;margin:0;font-size:.9rem}

.pill{display:inline-block;padding:.15rem .6rem;border-radius:999px;border:1px solid #2f3a63;color:#b9c2e8;font-size:.78rem;margin-right:.4rem}

.ok{border-color:#2e7d5b;color:#7ee0b0}

.empty{border:1px dashed #2f3a63;border-radius:16px;padding:2rem;text-align:center;color:#9aa4c7}

.item{background:#121a30;border:1px solid #232c4a;border-radius:12px;padding:.7rem 1rem;margin-bottom:.5rem}

mark{background:#4b3fa8;color:#fff;border-radius:3px;padding:0 2px}

</style>""", unsafe_allow_html=True)





# ---------- helpers ----------

def esc(x):

    return html.escape(str(x))





def safe_error(e: Exception) -> str:

    msg = f"{type(e).__name__}: {e}"

    for k, v in os.environ.items():

        if v and len(v) > 6 and any(t in k.upper() for t in ("KEY", "TOKEN", "SECRET", "PASSWORD")):

            msg = msg.replace(v, "***")

    return msg[:300]





def text_of(x):

    if x is None:

        return ""

    if isinstance(x, str):

        return x

    try:

        return json.dumps(x, ensure_ascii=False, indent=2) if isinstance(x, (dict, list)) else str(x)

    except Exception:

        return str(x)





def db():

    DB_PATH.parent.mkdir(exist_ok=True)

    con = sqlite3.connect(DB_PATH)

    con.row_factory = sqlite3.Row

    con.execute("""CREATE TABLE IF NOT EXISTS analyses(id TEXT PRIMARY KEY, created TEXT, title TEXT,

        source_type TEXT, source_label TEXT, language TEXT, summary TEXT, transcript TEXT,

        action_items TEXT, key_decisions TEXT, open_questions TEXT)""")

    return con





def save_analysis(a):

    with db() as con:

        con.execute("INSERT OR REPLACE INTO analyses VALUES(?,?,?,?,?,?,?,?,?,?,?)",

                    tuple(a[k] for k in ("id", "created", "title", "source_type", "source_label", "language",

                                         "summary", "transcript", "action_items", "key_decisions", "open_questions")))





def list_analyses(limit=100):

    with db() as con:

        return con.execute("SELECT id,created,title,source_type,language FROM analyses ORDER BY created DESC LIMIT ?",

                           (limit,)).fetchall()





def load_analysis(aid):

    with db() as con:

        r = con.execute("SELECT * FROM analyses WHERE id=?", (aid,)).fetchone()

    return dict(r) if r else None





def delete_analysis(aid):

    with db() as con:

        con.execute("DELETE FROM analyses WHERE id=?", (aid,))

    st.session_state.chains.pop(aid, None)

    st.session_state.chats.pop(aid, None)

    if st.session_state.active and st.session_state.active["id"] == aid:

        st.session_state.active = None





def go(page):

    st.session_state.page = page


def sync_page():
    """Copy the sidebar radio selection into the app routing state."""
    st.session_state.page = st.session_state.navigation_page





for k, v in {"page": "Dashboard", "active": None, "chains": {}, "chats": {}, "busy": False}.items():

    st.session_state.setdefault(k, v)





# Keep the widget key separate from the routing state.
st.session_state.navigation_page = st.session_state.page


# ---------- sidebar ----------

with st.sidebar:

    st.markdown(f"### 🎬 {APP_NAME}")

    st.caption("Summarize, analyze and chat with videos and recordings using AI.")

    st.radio("Navigation", PAGES, key="navigation_page", on_change=sync_page, label_visibility="collapsed")

    st.divider()

    st.caption("Transcription engines")

    st.markdown("<span class='pill'>English → Whisper</span><span class='pill'>Hinglish → Sarvam AI</span>",

                unsafe_allow_html=True)

    st.divider()

    st.caption(f"v{APP_VERSION} · local app")





# ---------- pages ----------

def page_dashboard():

    st.markdown("<div class='hero'><h1>Turn Videos into <span class='accent'>Actionable Intelligence</span></h1>"

                "<p>Summarize, analyze and search YouTube videos and recordings with AI — get transcripts, action items, "

                "decisions, and ask questions in chat.</p></div>", unsafe_allow_html=True)

    st.button("Analyze a Video", type="primary", on_click=go, args=("New Analysis",))

    st.write("")

    feats = [("✨ AI Summaries", "Concise executive summaries."), ("📝 Transcript Generation", "Full searchable transcript."),

             ("✅ Action Item Extraction", "Tasks pulled from the content."), ("🔑 Key Decision Detection", "Decisions made, at a glance."),

             ("💬 Ask Questions", "Chat with your video via RAG.")]

    cols = st.columns(3)

    for i, (t, d) in enumerate(feats):

        cols[i % 3].markdown(f"<div class='card'><h4>{t}</h4><p>{d}</p></div>", unsafe_allow_html=True)

        if i % 3 == 2:

            cols = st.columns(3)

    st.subheader("Recent analyses")

    rows = list_analyses(5)

    if not rows:

        st.markdown("<div class='empty'><h4>No analyses yet</h4>Run your first analysis to see it here.</div>",

                    unsafe_allow_html=True)

    for r in rows:

        c1, c2 = st.columns([5, 1])

        c1.markdown(f"<div class='item'><b>{esc(r['title'])}</b><br><span class='pill'>{esc(r['language'])}</span>"

                    f"<span class='pill'>{esc(r['source_type'])}</span><span class='pill'>{esc(r['created'][:16])}</span></div>",

                    unsafe_allow_html=True)

        if c2.button("Open", key=f"open_{r['id']}"):

            st.session_state.active = load_analysis(r["id"])

            st.session_state.page = "My Analysis"

            st.rerun()





def run_analysis(source, source_type, label, lang_key):

    from core.pipeline import run_pipeline  # lazy: keeps UI start fast

    code, engine = ENGINES[lang_key]

    with st.status(f"Analyzing with {engine}…", expanded=True) as status:

        def on_stage(n, msg):

            st.write(f"**Step {n} of 5** · {msg}…")

        res = run_pipeline(source, code, on_stage=on_stage)

        status.update(label="Analysis complete", state="complete")

    if not str(res.get("transcript", "")).strip():

        raise ValueError("The transcript is empty — nothing could be transcribed from this source.")

    a = {"id": uuid.uuid4().hex, "created": datetime.now().isoformat(timespec="seconds"), "title": text_of(res["title"]).strip() or "Untitled",

         "source_type": source_type, "source_label": label, "language": lang_key, "summary": text_of(res["summary"]),

         "transcript": text_of(res["transcript"]), "action_items": text_of(res["action_items"]),

         "key_decisions": text_of(res["key_decisions"]), "open_questions": text_of(res["open_questions"])}

    save_analysis(a)

    st.session_state.chains[a["id"]] = res["rag_chain"]

    st.session_state.chats[a["id"]] = []

    st.session_state.active = a





def page_new():

    st.header("New Analysis")

    st.caption("Provide a YouTube link **or** upload a file. Supported: " + ", ".join(sorted(e[1:].upper() for e in ALLOWED_EXT)) + ".")

    lang_key = st.radio("Language", list(ENGINES), horizontal=True,

                        help="English uses Whisper; Hinglish uses Sarvam AI.")

    st.info(f"Selected engine: **{ENGINES[lang_key][1]}**")

    c1, c2 = st.columns(2)

    url = c1.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=…").strip()

    up = c2.file_uploader("…or upload audio/video", type=[e[1:] for e in ALLOWED_EXT])

    if st.button("Analyze Video", type="primary", disabled=st.session_state.busy):

        if bool(url) == bool(up):

            st.error("Please provide exactly one source: a YouTube URL or an uploaded file.")

            return

        if url and not YT_RE.match(url):

            st.error("That doesn't look like a valid YouTube URL.")

            return

        if url and not url.startswith("http"):

            url = "https://" + url

        st.session_state.busy, tmp = True, None

        try:

            if up:

                ext = Path(up.name).suffix.lower()

                if ext not in ALLOWED_EXT:

                    st.error("Unsupported file type.")

                    return

                tmp = tempfile.mkdtemp(prefix="avs_")

                src = os.path.join(tmp, f"{uuid.uuid4().hex}{ext}")

                with open(src, "wb") as f:

                    f.write(up.getbuffer())

                run_analysis(src, "Upload", Path(up.name).name, lang_key)

            else:

                run_analysis(url, "YouTube", url, lang_key)

            st.session_state.page = "My Analysis"

            st.session_state.busy = False

            st.rerun()

        except Exception as e:

            msg = safe_error(e)
            lower_msg = msg.lower()

            if (
                "403" in msg
                or "forbidden" in lower_msg
                or "sign in" in lower_msg
                or "bot" in lower_msg
            ):
                st.error("YouTube could not provide the audio to this server.")
                st.info(
                    "You can still analyze this content by uploading an audio/video "
                    "file directly. Open New Analysis, leave the YouTube URL empty, "
                    "choose the file, and click Analyze Video."
                )
            else:
                st.error(f"Analysis failed. {msg}")

        finally:

            st.session_state.busy = False

            if tmp:

                shutil.rmtree(tmp, ignore_errors=True)





def dl_copy(label, text, fname, key):

    st.download_button(f"⬇ Download {label}", text, fname, key=f"dl_{key}")

    with st.expander("Copy"):

        st.code(text, language=None, wrap_lines=True)





def render_list(text, empty_msg, numbered=False, checklist=False):

    if not text.strip() or text.strip().lower() in {"none", "n/a", "[]", "no action items", "no questions"}:

        st.markdown(f"<div class='empty'>{esc(empty_msg)}</div>", unsafe_allow_html=True)

        return

    try:

        data = json.loads(text)

        items = data if isinstance(data, list) else None

    except Exception:

        items = None

    if items:

        for i, it in enumerate(items, 1):

            body = it if isinstance(it, str) else " · ".join(f"**{k}:** {v}" for k, v in it.items()) if isinstance(it, dict) else str(it)

            st.checkbox(body, key=f"cb_{hash(text)}_{i}") if checklist else st.markdown(f"<div class='item'>{i}. {esc(body)}</div>", unsafe_allow_html=True)

    else:

        st.markdown(text)  # plain model output, shown as-is





def render_chat(a):

    aid = a["id"]

    chain = st.session_state.chains.get(aid)

    if chain is None:

        st.info("Chat uses a retrieval index built from this transcript.")

        if st.button("Enable chat for this analysis", key=f"enable_{aid}"):

            try:

                from core.rag_engine import build_rag_chain

                with st.spinner("Preparing AI question-answering…"):

                    st.session_state.chains[aid] = build_rag_chain(a["transcript"])

                st.session_state.chats.setdefault(aid, [])

                st.rerun()

            except Exception as e:

                st.error(f"Could not prepare chat. {safe_error(e)}")

        return

    hist = st.session_state.chats.setdefault(aid, [])

    question = None

    cols = st.columns(2)

    for i, s in enumerate(SUGGESTED):

        if cols[i % 2].button(s, key=f"sg_{aid}_{i}"):

            question = s

    for m in hist:

        with st.chat_message(m["role"]):

            st.markdown(m["content"])

    typed = st.chat_input("Ask something about this video…", key=f"ci_{aid}")

    question = (typed or question or "").strip()

    if question:

        hist.append({"role": "user", "content": question})

        with st.chat_message("user"):

            st.markdown(question)

        with st.chat_message("assistant"):

            try:

                from core.rag_engine import ask_question

                with st.spinner("Thinking…"):

                    ans = text_of(ask_question(chain, question))

                st.markdown(ans)

                hist.append({"role": "assistant", "content": ans})

            except Exception as e:

                st.error(f"The model call failed. {safe_error(e)}")





def render_results(a):

    words = len(a["transcript"].split())

    sections = sum(bool(a[k].strip()) for k in ("summary", "action_items", "key_decisions", "open_questions"))

    st.markdown(f"## {esc(a['title'])}")

    st.markdown(f"<span class='pill ok'>✔ Analysis complete</span><span class='pill'>{esc(a['language'])}</span>"

                f"<span class='pill'>{esc(a['source_type'])}: {esc(a['source_label'])[:70]}</span>", unsafe_allow_html=True)

    m = st.columns(3)

    m[0].metric("Transcript words", f"{words:,}")

    m[1].metric("Sections completed", f"{sections}/4")

    m[2].metric("Analyzed", a["created"][:16].replace("T", " "))

    full = f"{a['title']}\n\nSUMMARY\n{a['summary']}\n\nTRANSCRIPT\n{a['transcript']}"

    st.download_button("⬇ Download transcript + summary", full, "analysis.txt", key=f"full_{a['id']}")

    tabs = st.tabs(["Overview", "Transcript", "Action Items", "Key Decisions", "Open Questions", "Ask AI"])

    with tabs[0]:

        st.subheader("Executive summary")

        st.markdown(a["summary"] or "_No summary was generated._")

        dl_copy("summary", a["summary"], "summary.txt", f"s_{a['id']}")

        st.caption("Title (copy):")

        st.code(a["title"], language=None)

    with tabs[1]:

        q = st.text_input("Search transcript", key=f"q_{a['id']}").strip()

        paras = [p for p in re.split(r"(?<=[.!?।])\s+", a["transcript"]) if p.strip()]

        paras = [" ".join(paras[i:i + 5]) for i in range(0, len(paras), 5)] or [a["transcript"]]

        if q:

            hits = [p for p in paras if q.lower() in p.lower()]

            st.caption(f"{len(hits)} matching passage(s)")

            for p in hits[:50]:

                marked = re.sub("(?i)(" + re.escape(esc(q)) + ")", r"<mark>\1</mark>", esc(p))

                st.markdown(f"<div class='item'>{marked}</div>", unsafe_allow_html=True)

        else:

            with st.container(height=450):

                for p in paras:

                    st.write(p)

        dl_copy("transcript", a["transcript"], "transcript.txt", f"t_{a['id']}")

    with tabs[2]:

        render_list(a["action_items"], "No action items were found.", checklist=True)

        dl_copy("action items", a["action_items"], "action_items.txt", f"a_{a['id']}")

    with tabs[3]:

        render_list(a["key_decisions"], "No key decisions were detected.")

    with tabs[4]:

        render_list(a["open_questions"], "No open questions were found in this transcript.")

        dl_copy("questions", a["open_questions"], "open_questions.txt", f"o_{a['id']}")

    with tabs[5]:

        render_chat(a)





def page_my():

    st.header("My Analysis")

    rows = list_analyses()

    if not rows:

        st.markdown("<div class='empty'><h4>Nothing saved yet</h4>Your completed analyses will appear here.</div>",

                    unsafe_allow_html=True)

        st.button("Start a new analysis", on_click=go, args=("New Analysis",))

        return

    ids = [r["id"] for r in rows]

    labels = {r["id"]: f"{r['title']} — {r['created'][:16].replace('T', ' ')}" for r in rows}

    cur = st.session_state.active["id"] if st.session_state.active else None

    idx = ids.index(cur) if cur in ids else 0

    c1, c2 = st.columns([5, 1])

    sel = c1.selectbox("Saved analyses", ids, index=idx, format_func=labels.get)

    if c2.button("🗑 Delete", help="Remove this analysis from history"):

        delete_analysis(sel)

        st.rerun()

    if not st.session_state.active or st.session_state.active["id"] != sel:

        st.session_state.active = load_analysis(sel)

    if st.session_state.active:

        render_results(st.session_state.active)





def page_about():

    st.header("Settings / About")

    st.write(f"**{APP_NAME}** v{APP_VERSION} turns YouTube videos and recordings into summaries, transcripts, "

             "action items, decisions, open questions and a RAG-powered chat.")

    st.markdown("- English → **Whisper**\n- Hinglish → **Sarvam AI**\n- LLM / RAG → your existing Groq + LangChain backend")

    st.caption("History is stored locally in `data/history.db` (title, summary, transcript, results — never API keys or audio). "

               "Chat indexes are rebuilt on demand when reopening an old analysis. This is a local single-user app: no auth or cloud sync.")

    st.caption("API keys are read from `.env` and never displayed.")

    if st.button("Clear all history"):

        for r in list_analyses(10_000):

            delete_analysis(r["id"])

        st.success("History cleared.")





{"Dashboard": page_dashboard, "New Analysis": page_new, "My Analysis": page_my, "Settings / About": page_about}[st.session_state.page]()
