import os
import io
import shutil
import uuid
from typing import Optional, List
from datetime import datetime

import urllib.parse

from fastapi import (
    FastAPI, Request, Form, UploadFile, File, Depends, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from database import engine, Base, SessionLocal
import models
import crud
from auth import hash_password, verify_password, get_db, get_current_user, require_admin
import uvicorn

# --- Подготовка директорий ---
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/images", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="!secret_dev_change_me!")

# --- Статика и шаблоны ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Создание таблиц ---
Base.metadata.create_all(bind=engine)


# --- Создание и исправление дефолтного админа ---
def create_default_admin():
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter_by(username="admin").first()
        if admin:
            # Принудительно обновляем пароль, если он был битый в SQL
            admin.hashed_password = hash_password("admin")
            if not admin.email:
                admin.email = "admin@alibi.ru"
            db.commit()
            print("✅ Admin password fixed to 'admin'")
        else:
            a = models.User(
                username="admin",
                email="admin@alibi.ru",
                hashed_password=hash_password("admin"),
                is_admin=True,
                is_active=True
            )
            db.add(a)
            db.commit()
            print("✅ Created default admin (admin/admin).")
    finally:
        db.close()


create_default_admin()


# --- Хелперы ---
def save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1]
    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join("static", "uploads", safe_name)
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return f"uploads/{safe_name}"


# --- Маршруты ---
@app.get("/", response_class=HTMLResponse)
def index(request: Request, q: Optional[str] = None, genre: Optional[str] = None,
          difficulty: Optional[str] = None, sort: Optional[str] = None,
          skip: int = 0, db: Session = Depends(get_db)):
    filters = {"q": q, "genre": genre, "difficulty": difficulty, "sort": sort}
    quests = crud.get_quests(db, skip=skip, limit=15, filters=filters)
    try:
        user = get_current_user(request, db)
    except:
        user = None
    return templates.TemplateResponse("index.html", {
        "request": request, "quests": quests, "user": user, "skip": skip, "now": datetime.now
    })


@app.get("/quest/{quest_id}", response_class=HTMLResponse)
def quest_detail(request: Request, quest_id: int, db: Session = Depends(get_db)):
    quest = crud.get_quest(db, quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    booked_slots = crud.get_booked_slots_for_date(db, quest_id, datetime.now().strftime('%Y-%m-%d'))
    try:
        user = get_current_user(request, db)
    except:
        user = None

    return templates.TemplateResponse("quest_detail.html", {
        "request": request, "quest": quest, "user": user, "booked_slots": booked_slots, "now": datetime.now
    })


@app.get("/api/available-slots")
def get_available_slots(quest_id: int, date: str, db: Session = Depends(get_db)):
    booked_slots = crud.get_booked_slots_for_date(db, quest_id, date)
    return JSONResponse(booked_slots)


@app.post("/book")
def book(request: Request, quest_id: int = Form(...), date: str = Form(...), timeslot: str = Form(...),
         db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    booking = crud.create_booking(db, user_id=user.id, quest_id=quest_id, date=date, timeslot=timeslot)
    if not booking:
        return JSONResponse({"success": False, "message": "Слот уже занят"}, status_code=400)
    return JSONResponse({"success": True, "message": "Бронь создана"})


@app.get("/my-bookings", response_class=HTMLResponse)
def my_bookings(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    bookings = crud.get_user_bookings(db, user.id)
    return templates.TemplateResponse("my_bookings.html", {
        "request": request, "user": user, "bookings": bookings, "now": datetime.now
    })


# --- Auth ---
@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(username=username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"})
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
def register_post(request: Request, username: str = Form(...), email: str = Form(None), password: str = Form(...),
                  db: Session = Depends(get_db)):
    if db.query(models.User).filter_by(username=username).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Имя занято"})

    u = models.User(username=username, email=email, hashed_password=hash_password(password), is_admin=False)
    db.add(u)
    db.commit()
    request.session["user_id"] = u.id
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# --- Admin ---
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db), user=Depends(require_admin)):
    quests = crud.get_quests(db, skip=0, limit=1000, filters={})
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, "quests": quests, "user": user, "now": datetime.now
    })


@app.post("/admin/add")
def add_post(request: Request, title: str = Form(...), description: str = Form(""),
             organizer_email: str = Form("alibi@mail.ru"), price: int = Form(2000),
             genres: List[str] = Form(...), difficulty: str = Form(""),
             fear_level: int = Form(1), players: int = Form(2),
             image: Optional[UploadFile] = File(None), clipboard_image: str = Form(None),
             db: Session = Depends(get_db), user=Depends(require_admin)):
    image_path = None
    if clipboard_image and clipboard_image.startswith('data:image'):
        import base64
        image_data = clipboard_image.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        safe_name = f"{uuid.uuid4().hex}.png"
        dest = os.path.join("static", "uploads", safe_name)
        with open(dest, "wb") as f:
            f.write(image_bytes)
        image_path = f"uploads/{safe_name}"
    elif image and image.filename:
        image_path = save_upload(image)

    new_quest = models.Quest(
        title=title, description=description, organizer_email=organizer_email,
        price=price, genre=", ".join(genres), difficulty=difficulty,
        fear_level=fear_level, min_players=2, max_players=players, image_path=image_path
    )
    db.add(new_quest)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/edit/{quest_id}")
def edit_post(request: Request, quest_id: int, title: str = Form(...), description: str = Form(""),
              organizer_email: str = Form("alibi@mail.ru"), price: int = Form(2000),
              genres: List[str] = Form(...), difficulty: str = Form(""),
              fear_level: int = Form(1), players: int = Form(2),
              image: Optional[UploadFile] = File(None), db: Session = Depends(get_db), user=Depends(require_admin)):
    quest = crud.get_quest(db, quest_id)
    if image and image.filename:
        quest.image_path = save_upload(image)

    quest.title, quest.description = title, description
    quest.organizer_email, quest.price = organizer_email, price
    quest.genre, quest.difficulty = ", ".join(genres), difficulty
    quest.fear_level, quest.max_players = fear_level, players
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.get("/admin/bookings", response_class=HTMLResponse)
def admin_bookings(request: Request, quest_id: Optional[int] = None, db: Session = Depends(get_db),
                   user=Depends(require_admin)):
    bookings = crud.get_quest_bookings(db, quest_id) if quest_id else crud.get_all_bookings(db)
    quests = crud.get_quests(db, skip=0, limit=1000, filters={})
    return templates.TemplateResponse("admin_bookings.html", {
        "request": request, "bookings": bookings, "quests": quests, "user": user, "now": datetime.now
    })


@app.post("/admin/delete-booking/{booking_id}")
def admin_delete_booking(booking_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    crud.delete_booking(db, booking_id)
    return RedirectResponse("/admin/bookings", status_code=303)


@app.post("/admin/delete/{quest_id}")
def admin_delete(request: Request, quest_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    if crud.has_quest_bookings(db, quest_id):
        return RedirectResponse("/admin?error=has_bookings", status_code=303)
    crud.delete_quest(db, quest_id)
    return RedirectResponse("/admin", status_code=303)


# --- Документы (Заявление и Чек) ---
@app.post("/download-statement")
async def download_statement(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    doc = Document()
    doc.add_heading('Заявление об отказе от претензий', 0)
    doc.add_paragraph(f"Я, {data['full_name']}, пасспорт {data['passport_series']} {data['passport_number']}")
    doc.add_paragraph(f"Добровольно принимаю участие в квесте: {data['quest_title']}")
    doc.add_paragraph(f"Дата: {datetime.now().strftime('%d.%m.%Y')}")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return StreamingResponse(buffer,
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f"attachment; filename=statement.docx"})


@app.post("/download-receipt")
async def download_receipt(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    data = await request.json()
    # Упрощенная генерация (текстовый файл для примера, так как PDF требует шрифтов)
    buffer = io.BytesIO()
    receipt_text = f"ЧЕК\nКвест: {data['quest_title']}\nЦена: {data['quest_price']} руб\nКлиент: {user.username}\nДата: {datetime.now()}"
    buffer.write(receipt_text.encode('utf-8'))
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="text/plain",
                             headers={"Content-Disposition": "attachment; filename=receipt.txt"})


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)