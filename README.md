# ReviseAI

ReviseAI is a Flask app that turns course notes into a study summary, a multiple-choice quiz, or both. Enter text in the form or upload a PDF, DOCX, or TXT file.

## What it does

- Generates summaries and quizzes through the Groq API.
- Lets you select a quiz difficulty: Facile, Moyen, or Difficile.
- Saves generated sessions and scores in SQLite by default, with optional MySQL support.
- Checks quiz answers in the browser and can export the corrected study sheet as a PDF.

## Requirements

- Python 3.10 or later
- A Groq API key
- MySQL only if you choose it instead of the default SQLite database

## Setup (Windows PowerShell)

Run these commands from the `ReviseAi` directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `GROQ_API_KEY` to your own key. Do not share or commit this file; it is ignored by Git.

The default Groq model is `openai/gpt-oss-120b`. If it is unavailable, the app tries `openai/gpt-oss-20b`. Set `GROQ_MODEL` in `.env` to choose another model.

## Start the app

From the same directory, with the virtual environment active:

```powershell
python -m flask --app app run
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Database

SQLite is the default and needs no separate service. The app creates its table on first use and stores data in `instance/reviseai.sqlite3`.

To use MySQL instead:

1. Run `database.sql` to create the database and table.
2. Set `DB_TYPE=mysql` in `.env`.
3. Configure `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`.
4. Start the MySQL service before running Flask.

## Tests

From the `ReviseAi` directory:

```powershell
python -m unittest discover -s tests -v
```

Tests use mocked Groq responses and a temporary SQLite database; they do not call the Groq API.

## Upload limits

The app accepts PDF, DOCX, and TXT files up to 16 MB. Extracted course text is limited to 12,000 characters. Scanned PDFs without selectable text and image uploads are not supported.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Required | Groq API key |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Preferred Groq model |
| `DB_TYPE` | `sqlite` | `sqlite` or `mysql` |
| `SQLITE_DB_PATH` | `instance/reviseai.sqlite3` | SQLite file path |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `root` | MySQL username |
| `DB_PASSWORD` | Empty | MySQL password |
| `DB_NAME` | `aiquizdb` | MySQL database |
