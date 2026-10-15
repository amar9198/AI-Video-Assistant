@echo off
cd /d %~dp0
if not exist venv (
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
)
if not exist .env (
    copy .env.example .env
    notepad .env
)
venv\Scripts\streamlit run app.py
pause