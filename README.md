# Universal Result Checker

FastAPI-powered PDF roll number extraction, exam result indexing, and candidate result search portal.

Downloaded from: `https://github.com/testbook-website/universal-result-checker`

---

## 🚀 Features

* **PDF Roll Number Extractor:** Automatically extracts roll numbers from merit list PDFs using PyMuPDF (`extractor.py`) with optional custom Regex patterns.
* **Candidate Result Search Portal:** Clean public frontend (`templates/index.html`) for students to look up roll numbers.
* **Admin Dashboard:** Password-protected `/admin` panel to upload result PDFs, toggle active exams, manage defaults, and monitor total indexed counts.
* **Database Support:** Seamless SQLite database (`sql_app.db`) out-of-the-box, with optional PostgreSQL support via `DATABASE_URL`.
* **Google Sheets Webhook:** Optional background synchronization to Google Sheets via Google Apps Script (`APPS_SCRIPT_DEPLOYMENT_ID`).

---

## 📁 Project Structure

```
universal-result-checker/
├── templates/
│   ├── admin.html       # Admin control panel UI
│   └── index.html       # Candidate result search UI
├── .env.example         # Environment template
├── .gitignore           # Git ignore list
├── database.py          # SQLAlchemy database engine and session
├── extractor.py         # PyMuPDF roll number parser
├── main.py              # FastAPI application routes & background tasks
├── models.py            # SQLAlchemy database models (Exam, RollNumber)
├── requirements.txt     # Python package dependencies
└── README.md            # Documentation
```

---

## 🛠️ How to Run

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment (Optional):**
   Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```

3. **Start the Server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. **Access the Application:**
   * Search Portal: `http://localhost:8000/`
   * Admin Panel: `http://localhost:8000/admin` (Default password: `SEO@7730`)
