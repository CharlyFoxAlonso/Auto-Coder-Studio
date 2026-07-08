@echo off
echo Starting Autonomous Coder Agent...
echo Activating Virtual Environment...

:: Check if .venv exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

:: Activate venv and install requirements
call .venv\Scripts\activate
echo Installing/Updating dependencies...
pip install -r requirements.txt

echo.
echo Starting Streamlit App...
streamlit run app.py

pause