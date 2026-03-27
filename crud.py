from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
import models
from datetime import datetime, date, timedelta
from typing import Optional, List


def get_quests(db: Session, skip: int = 0, limit: int = 12, filters: dict = None):
    """
    Поиск квестов с использованием PostgreSQL функции search_quests()
    """
    if filters is None:
        filters = {}

    result = db.execute(
        text("""
            SELECT * FROM search_quests(
                :p_search, 
                :p_genres, 
                :p_difficulties, 
                :p_max_fear_level,
                :p_min_players,
                :p_max_players,
                :p_min_rating,
                :p_sort_by, 
                :p_limit, 
                :p_offset
            )
        """),
        {
            "p_search": filters.get("q"),
            "p_genres": filters.get("genre") if filters.get("genre") else None,
            "p_difficulties": filters.get("difficulty") if filters.get("difficulty") else None,
            "p_max_fear_level": int(filters["fear_level"]) if filters.get("fear_level") else None,
            "p_min_players": int(filters["players"]) if filters.get("players") else None,
            "p_max_players": int(filters["players"]) if filters.get("players") else None,
            "p_min_rating": float(filters["min_rating"]) if filters.get("min_rating") else None,
            "p_sort_by": filters.get("sort") if filters.get("sort") else "title_asc",
            "p_limit": limit,
            "p_offset": skip
        }
    )

    quests = []
    for row in result:
        quest = models.Quest(
            id=row.id,
            title=row.title,
            description=row.description,
            genre=row.genre,
            difficulty=row.difficulty,
            fear_level=row.fear_level,
            price=row.price,
            address=row.address,
            image_data=row.image_data,
            avg_rating=row.avg_rating,
            min_players=row.min_players,
            max_players=row.max_players
        )
        quests.append(quest)

    return quests


def get_quest(db: Session, quest_id: int):
    """Получение одного квеста по ID"""
    return db.query(models.Quest).filter(
        models.Quest.id == quest_id,
        models.Quest.is_active == True
    ).first()


def create_booking(db: Session, user_id: int, quest_id: int, date: str, timeslot: str,
                   payment_method: str, participants_count: int = 2, prepayment: int = None):
    """Создание бронирования с указанием количества участников"""
    try:
        booking_datetime = datetime.strptime(f"{date} {timeslot}", "%Y-%m-%d %H:%M")
        booking_date = booking_datetime.date()
        booking_time = booking_datetime.time()

        user = db.query(models.User).filter(models.User.id == user_id).first()
        quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()

        if not user or not quest:
            print(f"User or quest not found: user={user_id}, quest={quest_id}")
            return None

        # Проверяем, что количество участников не превышает максимальное
        if participants_count < quest.min_players or participants_count > quest.max_players:
            print(f"Invalid participants count: {participants_count} (min={quest.min_players}, max={quest.max_players})")
            return None

        schedule = db.query(models.Schedule).filter(
            models.Schedule.quest_id == quest_id,
            models.Schedule.schedule_date == booking_date,
            models.Schedule.start_time == booking_time,
            models.Schedule.is_available == True
        ).first()

        if not schedule:
            end_time = (booking_datetime + timedelta(hours=1)).time()
            schedule = models.Schedule(
                quest_id=quest_id,
                schedule_date=booking_date,
                start_time=booking_time,
                end_time=end_time,
                max_slots=6,  # Максимум слотов (можно сделать настраиваемым)
                booked_slots=0,
                is_available=True
            )
            db.add(schedule)
            db.flush()

        if schedule.booked_slots + participants_count > schedule.max_slots:
            print(f"Slot full: booked_slots={schedule.booked_slots}, participants={participants_count}, max_slots={schedule.max_slots}")
            return None

        if prepayment is None:
            prepayment = quest.price // 2

        booking = models.Booking(
            user_id=user_id,
            quest_id=quest_id,
            schedule_id=schedule.id,
            status_id=1,
            booking_date_time=booking_datetime,
            participants_count=participants_count,
            total_price=quest.price,
            prepayment=prepayment,
            payment_method=payment_method,
            payment_status='prepayment_pending',
            customer_name=user.username,
            customer_phone="Не указан",
            customer_email=user.email
        )

        db.add(booking)
        schedule.booked_slots += participants_count

        db.commit()
        db.refresh(booking)
        return booking

    except Exception as e:
        print(f"Booking error: {e}")
        db.rollback()
        return None


def get_user_bookings(db: Session, user_id: int):
    """Получение бронирований пользователя"""
    result = db.execute(
        text("SELECT * FROM get_user_bookings_with_reviews(:user_id)"),
        {"user_id": user_id}
    )

    bookings = []
    for row in result:
        booking = db.query(models.Booking).filter(
            models.Booking.id == row.booking_id
        ).first()
        if booking:
            booking.can_cancel = row.can_cancel
            booking.can_review = row.can_review
            booking.has_review = row.has_review
            booking.hours_until_booking = row.hours_until_booking
            bookings.append(booking)

    return bookings


def get_all_bookings(db: Session):
    """Получение всех бронирований (админка)"""
    return db.query(models.Booking).options(
        joinedload(models.Booking.user),
        joinedload(models.Booking.quest),
        joinedload(models.Booking.schedule)
    ).order_by(models.Booking.booking_date_time.desc()).all()


def get_quest_statistics(db: Session):
    """Получение статистики по квестам"""
    result = db.execute(text("SELECT * FROM quest_statistics"))
    return result.fetchall()


def search_quests_by_text(db: Session, search_text: str, limit: int = 10):
    """Быстрый текстовый поиск"""
    result = db.execute(
        text("SELECT * FROM search_quests_by_text(:search_text, :limit)"),
        {"search_text": search_text, "limit": limit}
    )
    return result.fetchall()


def get_quest_bookings(db: Session, quest_id: int):
    """Получение бронирований для конкретного квеста"""
    return db.query(models.Booking).filter(
        models.Booking.quest_id == quest_id
    ).order_by(models.Booking.booking_date_time.desc()).all()


def has_quest_bookings(db: Session, quest_id: int) -> bool:
    """Проверка наличия активных бронирований у квеста"""
    return db.query(models.Booking).filter(
        models.Booking.quest_id == quest_id,
        models.Booking.booking_date_time >= datetime.now()
    ).count() > 0


def get_booked_slots_for_date(db: Session, quest_id: int, date_str: str):
    """Получение занятых слотов на дату"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        bookings = db.query(models.Booking).join(
            models.Schedule, models.Booking.schedule_id == models.Schedule.id
        ).filter(
            models.Schedule.quest_id == quest_id,
            models.Schedule.schedule_date == target_date,
            models.Booking.status_id != 3
        ).all()

        return [b.schedule.start_time.strftime("%H:%M") for b in bookings if b.schedule]
    except Exception as e:
        print(f"Error in get_booked_slots_for_date: {e}")
        return []


def delete_booking(db: Session, booking_id: int):
    """Удаление бронирования"""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if booking:
        db.delete(booking)
        db.commit()
        return True
    return False


def delete_quest(db: Session, quest_id: int):
    """Удаление квеста и всех связанных данных"""
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    if quest:
        bookings = db.query(models.Booking).filter(models.Booking.quest_id == quest_id).all()
        for booking in bookings:
            db.delete(booking)

        schedules = db.query(models.Schedule).filter(models.Schedule.quest_id == quest_id).all()
        for schedule in schedules:
            db.delete(schedule)

        db.delete(quest)
        db.commit()
        return True
    return False


def get_available_schedules(db: Session, quest_id: int, date_from: date = None):
    """Получение доступных слотов"""
    if not date_from:
        date_from = datetime.now().date()

    return db.query(models.Schedule).filter(
        models.Schedule.quest_id == quest_id,
        models.Schedule.schedule_date >= date_from,
        models.Schedule.is_available == True,
        models.Schedule.booked_slots < models.Schedule.max_slots
    ).order_by(models.Schedule.schedule_date, models.Schedule.start_time).all()