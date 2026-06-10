# Reference System

FastAPI-based literature assistant system.

## Local development

```bash
cd literature_assistant
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Server deployment

Runtime files are intentionally not committed:

- `literature_assistant/.env`
- `literature_assistant/instance/`
- `literature_assistant/uploads/`
- `literature_assistant/exports/`
- `literature_assistant/vector_store/`
- log files

On the server, create `.env` from `.env.example`, install requirements, then run:

```bash
cd literature_assistant
uvicorn main:app --host 127.0.0.1 --port 8000
```
