from fastapi import FastAPI, Depends, Request, Form, UploadFile, File, HTTPException, BackgroundTasks
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
        return
    
    deployment_id = deployment_id.strip()
    if deployment_id.startswith("http://") or deployment_id.startswith("https://"):
        url = deployment_id
    else:
        url = f"https://script.google.com/macros/s/{deployment_id}/exec"
    payload = {
        "exam_name": exam_name,
        "tier": tier,
        "roll_number": roll_number,
        "student_name": name,
        "mobile_number": mobile,
        "status": status
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )
        # Google Apps Script redirects on POST, urllib handles redirects automatically
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
    except Exception as e:
        print(f"Error sending data to Google Sheet: {e}")

app = FastAPI(title="Universal Result Checker")

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
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
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
async def toggle_default(exam_id: int, db: Session = Depends(get_db)):
    # Set all to false first
    db.query(models.Exam).update({models.Exam.is_default: False})
    # Set target to true
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if exam:
        exam.is_default = True
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/toggle_active/{exam_id}")
async def toggle_active(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if exam:
        exam.is_active = not exam.is_active
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/delete/{exam_id}")
async def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if exam:
        db.delete(exam)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)
