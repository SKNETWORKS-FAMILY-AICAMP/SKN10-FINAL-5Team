@echo off
echo Creating Python virtual environment...
uv venv .venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
uv pip install -r requirements.txt

echo Setup complete! You can now run the RAG system.
echo To activate the environment in the future, run: venv\Scripts\activate.bat 