from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, or_
import models
from datetime import datetime, date, timedelta
from typing import Optional, List


def get_quests(db: Session, skip: int = 0, limit: int = 12, filters: dict = None):
    query = db.query(models.Quest).filter(models.Quest.is_active == True)

    if filters:
        if filters.get("q"):
            search = f"%{filters['q']}%"
            query = query.filter(
                or_(
                    models.Quest.title.ilike(search),
                    models.Quest.description.ilike(search)
                )
            )

        if filters.get("genre"):
            genres = [g.strip() for g in filters["genre"].split(",")] if isinstance(filters["genre"], str) else filters[
                "genre"]
            genre_filters = [models.Quest.genre.ilike(f"%{genre}%") for genre in genres]
            query = query.filter(and_(*genre_filters))

        if filters.get("difficulty"):
            difficulties = [d.strip() for d in filters["difficulty"].split(",")] if isinstance(filters["difficulty"],
                                                                                               str) else filters[
                "difficulty"]
            query = query.filter(models.Quest.difficulty.in_(difficulties))

        if filters.get("players"):
            try:
                p = int(filters["players"])
                query = query.filter(models.Quest.min_players <= p, models.Quest.max_players >= p)
            except:
                pass

        if filters.get("fear_level"):
            try:
                fear = int(filters["fear_level"])
                query = query.filter(models.Quest.fear_level <= fear)
            except:
                pass

        if filters.get("sort"):
            if filters["sort"] == "price_low":
                query = query.order_by(models.Quest.price.asc())
            elif filters["sort"] == "price_high":
                query = query.order_by(models.Quest.price.desc())
            elif filters["sort"] == "title_asc":
                query = query.order_by(models.Quest.title.asc())
            elif filters["sort"] == "title_desc":
                query = query.order_by(models.Quest.title.desc())

    return query.offset(skip).limit(limit).all()


def get_quest(db: Session, quest_id: int):
    return db.query(models.Quest).filter(models.Quest.id == quest_id, models.Quest.is_active == True).first()


def has_quest_bookings(db: Session, quest_id: int) -> bool:
    """Проверяет, есть ли у квеста активные бронирования (будущие)"""
    return db.query(models.Booking).filter(
        models.Booking.quest_id == quest_id,
        models.Booking.booking_date_time >= datetime.now()
    ).count() > 0


def get_quest_bookings(db: Session, quest_id: int):
    return db.query(models.Booking).filter(
        models.Booking.quest_id == quest_id
    ).order_by(models.Booking.booking_date_time.desc()).all()


def get_booked_slots_for_date(db: Session, quest_id: int, date_str: str):
    """Возвращает список занятых временных слотов для квеста на указанную дату"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Ищем бронирования через расписание
        bookings = db.query(models.Booking).join(
            models.Schedule, models.Booking.schedule_id == models.Schedule.id
        ).filter(
            models.Schedule.quest_id == quest_id,
            models.Schedule.schedule_date == target_date,
            models.Booking.status_id != 3  # не cancelled
        ).all()

        return [b.schedule.start_time.strftime("%H:%M") for b in bookings if b.schedule]
    except Exception as e:
        print(f"Error in get_booked_slots_for_date: {e}")
        return []


def create_booking(db: Session, user_id: int, quest_id: int, date: str, timeslot: str):
    try:
        # Парсим дату и время
        booking_datetime = datetime.strptime(f"{date} {timeslot}", "%Y-%m-%d %H:%M")
        booking_date = booking_datetime.date()
        booking_time = booking_datetime.time()

        # Получаем пользователя и квест
        user = db.query(models.User).filter(models.User.id == user_id).first()
        quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()

        if not user or not quest:
            return None

        # Проверяем, есть ли уже слот в расписании
        schedule = db.query(models.Schedule).filter(
            models.Schedule.quest_id == quest_id,
            models.Schedule.schedule_date == booking_date,
            models.Schedule.start_time == booking_time,
            models.Schedule.is_available == True
        ).first()

        # Если слота нет, создаем его
        if not schedule:
            end_time = (booking_datetime + timedelta(hours=1)).time()
            schedule = models.Schedule(
                quest_id=quest_id,
                schedule_date=booking_date,
                start_time=booking_time,
                end_time=end_time,
                max_slots=2,  # Максимум 2 бронирования на слот
                booked_slots=0,
                is_available=True
            )
            db.add(schedule)
            db.flush()

        # Проверяем, есть ли свободные места
        if schedule.booked_slots >= schedule.max_slots:
            print(f"Слот занят: booked_slots={schedule.booked_slots}, max_slots={schedule.max_slots}")
            return None

        # Создаем бронирование
        booking = models.Booking(
            user_id=user_id,
            quest_id=quest_id,
            schedule_id=schedule.id,
            status_id=1,  # pending
            booking_date_time=booking_datetime,
            participants_count=2,
            total_price=quest.price,
            customer_name=user.username,
            customer_phone=user.phone or "Не указан",
            customer_email=user.email,
            payment_status='pending'
        )

        db.add(booking)
        db.flush()

        db.commit()
        db.refresh(booking)
        return booking

    except Exception as e:
        print(f"Booking error: {e}")
        db.rollback()
        return None


def get_user_bookings(db: Session, user_id: int):
    return db.query(models.Booking).filter(
        models.Booking.user_id == user_id
    ).options(
        joinedload(models.Booking.quest),
        joinedload(models.Booking.schedule)
    ).order_by(models.Booking.booking_date_time.desc()).all()


def get_all_bookings(db: Session):
    return db.query(models.Booking).options(
        joinedload(models.Booking.user),
        joinedload(models.Booking.quest),
        joinedload(models.Booking.schedule)
    ).order_by(models.Booking.booking_date_time.desc()).all()


def delete_booking(db: Session, booking_id: int):
    """Удаляет бронирование из БД"""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if booking:
        db.delete(booking)
        db.commit()
        return True
    return False


def delete_quest(db: Session, quest_id: int):
    """ПОЛНОСТЬЮ УДАЛЯЕТ квест из БД вместе со связанными записями"""
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    if quest:
        # Сначала удаляем все связанные бронирования
        bookings = db.query(models.Booking).filter(models.Booking.quest_id == quest_id).all()
        for booking in bookings:
            db.delete(booking)

        # Удаляем все связанное расписание
        schedules = db.query(models.Schedule).filter(models.Schedule.quest_id == quest_id).all()
        for schedule in schedules:
            db.delete(schedule)

        # Удаляем сам квест
        db.delete(quest)
        db.commit()
        return True
    return False


def delete_quest_force(db: Session, quest_id: int):
    """Принудительно удаляет квест даже с бронированиями"""
    return delete_quest(db, quest_id)


def get_available_schedules(db: Session, quest_id: int, date_from: date = None):
    """Получить доступные слоты для квеста"""
    if not date_from:
        date_from = datetime.now().date()

    return db.query(models.Schedule).filter(
        models.Schedule.quest_id == quest_id,
        models.Schedule.schedule_date >= date_from,
        models.Schedule.is_available == True,
        models.Schedule.booked_slots < models.Schedule.max_slots
    ).order_by(models.Schedule.schedule_date, models.Schedule.start_time).all()