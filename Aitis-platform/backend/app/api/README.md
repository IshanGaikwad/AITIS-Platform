
# AI Test Intelligence Platform – FastAPI Backend

This is a **real FastAPI backend implementation** for the AI Test Intelligence Platform.

## Features
- Story normalization
- Intent generation (deterministic + extensible for LLMs)
- Test case generation (happy, negative, edge)
- Gherkin scenario generation
- Automation code generation (Playwright)
- SQLite persistence via SQLAlchemy
- Clean service / repository architecture

## Run Locally
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
