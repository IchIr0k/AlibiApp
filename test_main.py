import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import uuid

from main import app
from auth import get_current_user, get_db
import models

client = TestClient(app)


# Вспомогательная функция для получения данных из реальной БД для тестов
def get_existing_data():
    db = next(get_db())
    try:
        user = db.query(models.User).first()
        quest = db.query(models.Quest).filter(models.Quest.is_active == True).first()
        return user, quest
    finally:
        db.close()


# --- ТЕСТЫ ---

# 1. ПОЗИТИВНЫЙ: Регистрация (уникальный пользователь)
def test_register_user_success():
    random_suffix = uuid.uuid4().hex[:6]
    response = client.post(
        "/register",
        data={
            "username": f"user_{random_suffix}",
            "email": f"test_{random_suffix}@mail.ru",
            "password": "password123"
        },
        follow_redirects=False
    )
    assert response.status_code == 303


# 2. ПОЗИТИВНЫЙ: Успешное бронирование
def test_book_quest_success():
    test_user, test_quest = get_existing_data()

    if not test_user or not test_quest:
        pytest.skip("В базе данных должен быть хотя бы один пользователь и один активный квест")

    # Мокаем текущего пользователя, используя реально существующего из БД
    app.dependency_overrides[get_current_user] = lambda: test_user

    future_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    response = client.post(
        "/book",
        data={
            "quest_id": test_quest.id,  # Используем ID существующего квеста
            "date": future_date,
            "timeslot": "14:00",
            "payment_method": "card",
            "participants_count": test_quest.min_players
        }
    )
    app.dependency_overrides = {}

    assert response.status_code == 200
    assert response.json()["success"] is True


# 3. НЕГАТИВНЫЙ: Бронирование менее чем за 24 часа
def test_book_quest_less_than_24h():
    test_user, test_quest = get_existing_data()
    if not test_user or not test_quest:
        pytest.skip("Нужны данные в БД")

    app.dependency_overrides[get_current_user] = lambda: test_user

    near_date = datetime.now().strftime("%Y-%m-%d")
    near_time = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")

    response = client.post(
        "/book",
        data={
            "quest_id": test_quest.id,
            "date": near_date,
            "timeslot": near_time,
            "payment_method": "card",
            "participants_count": test_quest.min_players
        }
    )
    app.dependency_overrides = {}

    assert response.status_code == 400
    assert "не менее чем за 24 часа" in response.json()["message"]


# 4. НЕГАТИВНЫЙ: Отзыв без оплаты
def test_submit_review_not_paid():
    test_user, _ = get_existing_data()
    app.dependency_overrides[get_current_user] = lambda: test_user

    response = client.post(
        "/submit-review",
        data={
            "booking_id": 99999,
            "rating": 5,
            "comment": "Тест"
        }
    )
    app.dependency_overrides = {}
    assert response.status_code in [400, 404]


# 5. НЕГАТИВНЫЙ: Вход с неверным паролем
def test_login_wrong_password():
    response = client.post(
        "/login",
        data={"username": "non_existent_user_99", "password": "wrong_password"}
    )
    assert response.status_code == 200
    assert "Неверный логин или пароль" in response.text