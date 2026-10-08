from fastapi import FastAPI, Depends, Request, Form, UploadFile, File, HTTPException, BackgroundTasks, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os
import shutil
import urllib.request
import json
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

from database import engine, get_db
import models
from extractor import extract_roll_numbers_from_pdf

# Create DB tables
models.Base.metadata.create_all(bind=engine)

def send_to_google_sheet(exam_name: str, tier: str, roll_number: str, name: str, mobile: str, status: str):
    deployment_id = os.getenv("APPS_SCRIPT_DEPLOYMENT_ID")
    if not deployment_id or not deployment_id.strip():
        print("[Google Sheets] APPS_SCRIPT_DEPLOYMENT_ID is not configured. Skipping sync.")
        return
    
    deployment_id = deployment_id.strip()
    if deployment_id.startswith("http://") or deployment_id.startswith("https://"):
        url = deployment_id
    else:
        url = f"https://script.google.com/macros/s/{deployment_id}/exec"
    
    # Ensure Web App URL ends with /exec
    if not url.endswith("/exec"):
        if "/exec" not in url:
            url = url.rstrip("/") + "/exec"
            
    import urllib.parse
    query_str = urllib.parse.urlencode({
        "name": name,
        "student_name": name,
        "rollNumber": roll_number,
        "roll_number": roll_number,
        "roll": roll_number,
        "mobile": mobile,
        "mobile_number": mobile,
        "phone": mobile,
        "exam_name": exam_name,
        "exam": exam_name,
        "tier": tier,
        "status": status,
        "zone": f"{exam_name} - {tier}"
    })
    
    get_url = f"{url}?{query_str}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 1. Primary: Send via GET query parameters (Fastest, 100% reliable with Google Apps Script 302 redirects)
    try:
        get_req = urllib.request.Request(get_url, headers=headers)
        with urllib.request.urlopen(get_req, timeout=20) as response:
            res_body = response.read().decode('utf-8', errors='ignore')
            print(f"[Google Sheets] Data successfully sent to Google Sheet: {res_body[:100]}")
            return
    except Exception as get_err:
        print(f"[Google Sheets] GET request failed ({get_err}). Attempting POST fallback...")

    # 2. Fallback: Send via JSON POST
    try:
        payload = {
            "name": name,
            "rollNumber": roll_number,
            "mobile": mobile,
            "exam_name": exam_name,
            "tier": tier,
            "status": status
        }
        data = json.dumps(payload).encode('utf-8')
        post_req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', 'User-Agent': headers['User-Agent']})
        with urllib.request.urlopen(post_req, timeout=20) as response:
            res_body = response.read().decode('utf-8', errors='ignore')
            print(f"[Google Sheets] Data successfully sent to Google Sheet via POST fallback: {res_body[:100]}")
    except Exception as post_err:
        print(f"[Google Sheets] Both GET and POST requests failed: {post_err}")

app = FastAPI(title="Universal Result Checker")

security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_password = os.getenv("ADMIN_PASSWORD", "SEO@7730")
    if credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# Setup templates and static
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- USER ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/exams")
def get_active_exams(db: Session = Depends(get_db)):
    exams = db.query(models.Exam).filter(models.Exam.is_active == True).all()
    return exams

@app.post("/api/check")
async def check_result(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    data = await request.json()
    exam_id = data.get("exam_id")
    roll_number = data.get("roll_number")
    name = data.get("name")
    mobile = data.get("mobile")
    
    if not exam_id or not roll_number or not name or not mobile:
        raise HTTPException(status_code=400, detail="Missing required fields: exam_id, roll_number, name, or mobile")
        
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    exists = db.query(models.RollNumber).filter(
        models.RollNumber.exam_id == exam_id,
        models.RollNumber.roll_number == roll_number
    ).first()
    
    status_str = "Qualified" if exists else "Not Qualified"
    
    # Trigger background task to forward lead data to Google Sheet
    background_tasks.add_task(
        send_to_google_sheet,
        exam_name=exam.exam_name,
        tier=exam.tier,
        roll_number=roll_number,
        name=name,
        mobile=mobile,
        status=status_str
    )
    
    return {"status": "success", "found": bool(exists)}

# --- ADMIN ROUTES ---

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, username: str = Depends(verify_admin), db: Session = Depends(get_db)):
    exams = db.query(models.Exam).all()
    # Add count of roll numbers
    for exam in exams:
        exam.count = db.query(models.RollNumber).filter(models.RollNumber.exam_id == exam.id).count()
    return templates.TemplateResponse(request=request, name="admin.html", context={"exams": exams})

@app.post("/admin/upload")
async def upload_exam(
    exam_name: str = Form(...),
    tier: str = Form(...),
    regex_pattern: str = Form(None),
    file: UploadFile = File(...),
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
        
    # Save PDF temporarily
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Extract roll numbers
    roll_numbers = extract_roll_numbers_from_pdf(file_path, regex_pattern)
    
    if not roll_numbers:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="No roll numbers could be detected or extracted from the PDF")
        
    # Create Exam record
    new_exam = models.Exam(exam_name=exam_name, tier=tier, is_default=False, is_active=True)
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)
    
    # Bulk insert roll numbers
    db_roll_numbers = [
        models.RollNumber(exam_id=new_exam.id, roll_number=rn)
        for rn in roll_numbers
    ]
    db.add_all(db_roll_numbers)
    db.commit()
    
    os.remove(file_path) # Clean up
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/toggle_default/{exam_id}")
async def toggle_default(exam_id: int, username: str = Depends(verify_admin), db: Session = Depends(get_db)):
    # Set all to false first
    db.query(models.Exam).update({models.Exam.is_default: False})
    # Set target to true
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if exam:
        exam.is_default = True
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/toggle_active/{exam_id}")
async def toggle_active(exam_id: int, username: str = Depends(verify_admin), db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if exam:
        exam.is_active = not exam.is_active
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/delete/{exam_id}")
async def delete_exam(exam_id: int, username: str = Depends(verify_admin), db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if exam:
        db.delete(exam)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)
