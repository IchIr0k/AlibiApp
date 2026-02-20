import os
import io
import shutil
import uuid
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import (
    FastAPI, Request, Form, UploadFile, File, Depends, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from docx import Document

from database import SessionLocal
import models
import crud
from auth import hash_password, verify_password, get_db, get_current_user, require_admin
import uvicorn


# --- Функция для получения текущего времени ---
def now_with_tz():
    return datetime.now().astimezone()


def naive_now():
    return datetime.now().replace(tzinfo=None)


# --- Подготовка директорий ---
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/images", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="!secret_dev_change_me!")

# --- Статика и шаблоны ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

print("✅ Подключение к существующей базе данных")


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
          difficulty: Optional[str] = None, fear_level: Optional[str] = None,
          players: Optional[str] = None, sort: Optional[str] = None,
          skip: int = 0, db: Session = Depends(get_db)):
    try:
        filters = {
            "q": q,
            "genre": genre,
            "difficulty": difficulty,
            "fear_level": fear_level,
            "players": players,
            "sort": sort
        }
        quests = crud.get_quests(db, skip=skip, limit=15, filters=filters)
    except Exception as e:
        print(f"Ошибка при загрузке квестов: {e}")
        quests = []

    try:
        user = get_current_user(request, db)
    except:
        user = None

    return templates.TemplateResponse("index.html", {
        "request": request,
        "quests": quests,
        "user": user,
        "skip": skip,
        "now": naive_now
    })


@app.get("/quest/{quest_id}", response_class=HTMLResponse)
def quest_detail(request: Request, quest_id: int, db: Session = Depends(get_db)):
    quest = crud.get_quest(db, quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    try:
        booked_slots = crud.get_booked_slots_for_date(db, quest_id, naive_now().strftime('%Y-%m-%d'))
    except:
        booked_slots = []

    try:
        user = get_current_user(request, db)
    except:
        user = None

    return templates.TemplateResponse("quest_detail.html", {
        "request": request,
        "quest": quest,
        "user": user,
        "booked_slots": booked_slots,
        "now": naive_now
    })


@app.get("/api/available-slots")
def get_available_slots(quest_id: int, date: str, db: Session = Depends(get_db)):
    try:
        booked_slots = crud.get_booked_slots_for_date(db, quest_id, date)
        return JSONResponse(booked_slots)
    except Exception as e:
        print(f"Error getting available slots: {e}")
        return JSONResponse([], status_code=500)


@app.post("/book")
def book(request: Request, quest_id: int = Form(...), date: str = Form(...), timeslot: str = Form(...),
         db: Session = Depends(get_db)):
    try:
        user = get_current_user(request, db)
        booking = crud.create_booking(db, user_id=user.id, quest_id=quest_id, date=date, timeslot=timeslot)
        if not booking:
            return JSONResponse({"success": False, "message": "Слот уже занят или произошла ошибка"}, status_code=400)
        return JSONResponse({"success": True, "message": "Бронь создана"})
    except HTTPException:
        return JSONResponse({"success": False, "message": "Необходимо авторизоваться"}, status_code=401)
    except Exception as e:
        print(f"Booking error: {e}")
        return JSONResponse({"success": False, "message": f"Ошибка: {str(e)}"}, status_code=500)


@app.get("/my-bookings", response_class=HTMLResponse)
def my_bookings(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user(request, db)
        bookings = crud.get_user_bookings(db, user.id)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)
    except Exception as e:
        print(f"Error loading bookings: {e}")
        bookings = []
        user = None

    return templates.TemplateResponse("my_bookings.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "now": naive_now
    })


# --- Auth ---
@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(username=username, is_active=True).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"})

    # Обновляем last_login
    user.last_login = now_with_tz()
    db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
def register_post(request: Request, username: str = Form(...), email: str = Form(...),
                  password: str = Form(...), phone: str = Form(""),
                  first_name: str = Form(""), last_name: str = Form(""),
                  db: Session = Depends(get_db)):
    # Проверяем существование пользователя
    if db.query(models.User).filter_by(username=username).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Имя занято"})

    if db.query(models.User).filter_by(email=email).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email уже используется"})

    # Создаем нового пользователя
    u = models.User(
        username=username,
        email=email,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
        hashed_password=hash_password(password),
        is_admin=False,
        is_active=True
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    request.session["user_id"] = u.id
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# --- Admin ---
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db), user=Depends(require_admin)):
    try:
        quests = crud.get_quests(db, skip=0, limit=1000, filters={})
        all_bookings = crud.get_all_bookings(db)
    except Exception as e:
        quests = []
        all_bookings = []
        print(f"Admin error: {e}")

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "quests": quests,
        "user": user,
        "now": naive_now,
        "quest_bookings": all_bookings
    })


@app.get("/admin/add", response_class=HTMLResponse)
def admin_add_form(request: Request, user=Depends(require_admin)):
    return templates.TemplateResponse("add_quest.html", {"request": request, "user": user})


@app.post("/admin/add")
def add_post(
        request: Request,
        title: str = Form(...),
        description: str = Form(...),
        genres: List[str] = Form(...),  # изменено с genre на genres
        difficulty: str = Form(...),
        fear_level: int = Form(...),
        max_players: int = Form(...),
        organizer_email: str = Form("alibi@mail.ru"),
        price: int = Form(2000),
        image: Optional[UploadFile] = File(None),
        clipboard_image: str = Form(None),
        db: Session = Depends(get_db),
        user=Depends(require_admin)
):
    try:
        image_path = None

        # Обработка изображения
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
            ext = os.path.splitext(image.filename)[1]
            safe_name = f"{uuid.uuid4().hex}{ext}"
            dest = os.path.join("static", "uploads", safe_name)
            content = image.file.read()
            with open(dest, "wb") as f:
                f.write(content)
            image_path = f"uploads/{safe_name}"

        # Объединяем выбранные жанры в строку
        genre_str = ", ".join(genres) if genres else "Не указан"

        # Создание квеста
        new_quest = models.Quest(
            title=title,
            description=description,
            genre=genre_str,  # сохраняем как строку
            difficulty=difficulty,
            fear_level=fear_level,
            max_players=max_players,
            min_players=2,  # значение по умолчанию
            organizer_email=organizer_email,
            price=price,
            image_path=image_path,
            is_active=True
        )
        db.add(new_quest)
        db.commit()

        return RedirectResponse("/admin", status_code=303)

    except Exception as e:
        print(f"Error adding quest: {e}")
        quests = crud.get_quests(db, skip=0, limit=1000, filters={})
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "quests": quests,
            "user": user,
            "error": f"Ошибка при добавлении квеста: {str(e)}",
            "now": naive_now
        })


@app.get("/admin/edit/{quest_id}", response_class=HTMLResponse)
def admin_edit_form(request: Request, quest_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    quest = crud.get_quest(db, quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return templates.TemplateResponse("edit_quest.html", {"request": request, "quest": quest, "user": user})


@app.post("/admin/edit/{quest_id}")
def edit_post(
        request: Request,
        quest_id: int,
        title: str = Form(...),
        description: str = Form(...),
        genres: List[str] = Form(...),  # изменено с genre на genres
        difficulty: str = Form(...),
        fear_level: int = Form(...),
        max_players: int = Form(...),
        organizer_email: str = Form("alibi@mail.ru"),
        price: int = Form(2000),
        image: Optional[UploadFile] = File(None),
        clipboard_image: str = Form(None),
        db: Session = Depends(get_db),
        user=Depends(require_admin)
):
    quest = crud.get_quest(db, quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # Обработка изображения
    if clipboard_image and clipboard_image.startswith('data:image'):
        import base64
        image_data = clipboard_image.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        safe_name = f"{uuid.uuid4().hex}.png"
        dest = os.path.join("static", "uploads", safe_name)
        with open(dest, "wb") as f:
            f.write(image_bytes)
        quest.image_path = f"uploads/{safe_name}"
    elif image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        safe_name = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join("static", "uploads", safe_name)
        content = image.file.read()
        with open(dest, "wb") as f:
            f.write(content)
        quest.image_path = f"uploads/{safe_name}"

    # Обновляем поля
    quest.title = title
    quest.description = description
    quest.genre = ", ".join(genres) if genres else "Не указан"
    quest.difficulty = difficulty
    quest.fear_level = fear_level
    quest.max_players = max_players
    quest.organizer_email = organizer_email
    quest.price = price

    db.commit()

    return RedirectResponse("/admin", status_code=303)


@app.get("/admin/bookings", response_class=HTMLResponse)
def admin_bookings(request: Request, quest_id: Optional[int] = None, db: Session = Depends(get_db),
                   user=Depends(require_admin)):
    try:
        if quest_id:
            bookings = crud.get_quest_bookings(db, quest_id)
        else:
            bookings = crud.get_all_bookings(db)
        quests = crud.get_quests(db, skip=0, limit=1000, filters={})
    except Exception as e:
        bookings = []
        quests = []
        print(f"Bookings error: {e}")

    return templates.TemplateResponse("admin_bookings.html", {
        "request": request,
        "bookings": bookings,
        "quests": quests,
        "user": user,
        "now": naive_now
    })


@app.post("/admin/delete-booking/{booking_id}")
def admin_delete_booking(booking_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    crud.delete_booking(db, booking_id)
    return RedirectResponse("/admin/bookings", status_code=303)


@app.post("/admin/delete/{quest_id}")
def admin_delete(request: Request, quest_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    # Проверяем наличие будущих бронирований
    if crud.has_quest_bookings(db, quest_id):
        # Если есть бронирования, показываем страницу с предупреждением
        quest = crud.get_quest(db, quest_id)
        bookings = crud.get_quest_bookings(db, quest_id)
        quests = crud.get_quests(db, skip=0, limit=1000, filters={})
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "quests": quests,
            "user": user,
            "error": f"Невозможно удалить квест '{quest.title}'. У него есть активные бронирования.",
            "blocked_quest_id": quest_id,
            "quest_bookings": bookings,
            "now": naive_now
        })

    # ПОЛНОЕ УДАЛЕНИЕ из БД
    crud.delete_quest(db, quest_id)
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/delete-quest-with-bookings/{quest_id}")
def admin_delete_quest_with_bookings(quest_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    # Принудительное удаление квеста вместе со всеми бронированиями
    crud.delete_quest(db, quest_id)  # Функция уже удаляет всё связанное
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/delete-all-bookings/{quest_id}")
def admin_delete_all_bookings(quest_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    bookings = crud.get_quest_bookings(db, quest_id)
    for booking in bookings:
        crud.delete_booking(db, booking.id)
    return RedirectResponse(f"/admin?highlight={quest_id}", status_code=303)


@app.post("/admin/delete-quest-with-bookings/{quest_id}")
def admin_delete_quest_with_bookings(quest_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    bookings = crud.get_quest_bookings(db, quest_id)
    for booking in bookings:
        crud.delete_booking(db, booking.id)
    crud.delete_quest(db, quest_id)
    return RedirectResponse("/admin", status_code=303)


# --- Документы ---
@app.post("/download-statement")
async def download_statement(request: Request):
    data = await request.json()
    doc = Document()
    doc.add_heading('Заявление об отказе от претензий', 0)
    doc.add_paragraph(f"Я, {data['full_name']}, паспорт {data['passport_series']} {data['passport_number']}")
    doc.add_paragraph(f"Добровольно принимаю участие в квесте: {data['quest_title']}")
    doc.add_paragraph(f"Дата: {naive_now().strftime('%d.%m.%Y')}")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=statement.docx"}
    )


@app.post("/download-receipt")
async def download_receipt(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user(request, db)
    except:
        user = None

    data = await request.json()
    buffer = io.BytesIO()
    receipt_text = f"""ЧЕК ОБ ОПЛАТЕ
─────────────────────
Квест: {data['quest_title']}
Цена: {data['quest_price']} руб
Клиент: {user.username if user else 'Гость'}
Дата: {naive_now().strftime('%d.%m.%Y %H:%M')}
─────────────────────
Спасибо за бронирование!"""
    buffer.write(receipt_text.encode('utf-8'))
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=receipt.txt"}
    )


# --- API для проверки ---
@app.get("/api/quest-has-bookings/{quest_id}")
def api_quest_has_bookings(quest_id: int, db: Session = Depends(get_db)):
    has_bookings = crud.has_quest_bookings(db, quest_id)
    return JSONResponse({"has_bookings": has_bookings})


@app.get("/api/quests")
def api_get_quests(skip: int = 0, q: Optional[str] = None, genre: Optional[str] = None,
                   difficulty: Optional[str] = None, fear_level: Optional[str] = None,
                   players: Optional[str] = None, sort: Optional[str] = None,
                   db: Session = Depends(get_db)):
    filters = {
        "q": q,
        "genre": genre,
        "difficulty": difficulty,
        "fear_level": fear_level,
        "players": players,
        "sort": sort
    }
    quests = crud.get_quests(db, skip=skip, limit=15, filters=filters)
    return templates.TemplateResponse("_quest_cards.html", {"request": {}, "quests": quests})


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)