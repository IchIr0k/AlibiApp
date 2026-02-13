from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import models, schemas
from datetime import datetime


def get_quests(db: Session, skip: int = 0, limit: int = 12, filters: dict = None):
    query = db.query(models.Quest)
    if filters:
        if filters.get("q"):
            query = query.filter(models.Quest.title.ilike(f"%{filters['q']}%"))
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
    return query.offset(skip).limit(limit).all()


def get_quest(db: Session, quest_id: int):
    return db.query(models.Quest).filter(models.Quest.id == quest_id).first()


def has_quest_bookings(db: Session, quest_id: int) -> bool:
    return db.query(models.Booking).filter(models.Booking.quest_id == quest_id).count() > 0


def get_quest_bookings(db: Session, quest_id: int):
    return db.query(models.Booking).filter(models.Booking.quest_id == quest_id).order_by(
        models.Booking.booking_date_time.desc()).all()


def get_booked_slots_for_date(db: Session, quest_id: int, date_str: str):
    # Фильтруем DateTime поле по дате
    bookings = db.query(models.Booking).filter(
        models.Booking.quest_id == quest_id,
        func.date(models.Booking.booking_date_time) == date_str
    ).all()
    return [b.booking_date_time.strftime("%H:%M") for b in bookings]


def create_booking(db: Session, user_id: int, quest_id: int, date: str, timeslot: str):
    try:
        dt_obj = datetime.strptime(f"{date} {timeslot}", "%Y-%m-%d %H:%M")
        quest = get_quest(db, quest_id)
        user = db.query(models.User).filter(models.User.id == user_id).first()

        booking = models.Booking(
            user_id=user_id,
            quest_id=quest_id,
            booking_date_time=dt_obj,
            customer_name=user.username,
            customer_phone=user.phone or "Не указан",
            total_price=quest.price,
            status_id=1  # pending
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
    except Exception as e:
        print(f"Booking error: {e}")
        return None


def get_user_bookings(db: Session, user_id: int):
    return db.query(models.Booking).filter(models.Booking.user_id == user_id).order_by(
        models.Booking.booking_date_time.desc()).all()


def get_all_bookings(db: Session):
    return db.query(models.Booking).order_by(models.Booking.booking_date_time.desc()).all()


def delete_booking(db: Session, booking_id: int):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if booking:
        db.delete(booking)
        db.commit()
        return True
    return False


def delete_quest_bookings(db: Session, quest_id: int):
    db.query(models.Booking).filter(models.Booking.quest_id == quest_id).delete()
    db.commit()