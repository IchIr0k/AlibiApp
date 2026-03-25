from sqlalchemy.orm import Session
import models
from datetime import datetime


def can_user_review_quest(db: Session, user_id: int, quest_id: int) -> bool:
    """Проверяет, может ли пользователь оставить отзыв на квест"""

    # Ищем завершенные бронирования пользователя на этот квест
    booking = db.query(models.Booking).filter(
        models.Booking.user_id == user_id,
        models.Booking.quest_id == quest_id,
        models.Booking.booking_date_time < datetime.now(),  # квест уже прошел
        models.Booking.payment_status == 'prepayment_paid'  # предоплата внесена
    ).first()

    if not booking:
        return False

    # Проверяем, не оставлял ли пользователь уже отзыв на это бронирование
    existing_review = db.query(models.Review).filter(
        models.Review.booking_id == booking.id
    ).first()

    if existing_review:
        return False

    return True


def get_user_bookings_for_review(db: Session, user_id: int):
    """Получает завершенные бронирования пользователя, на которые можно оставить отзыв"""

    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user_id,
        models.Booking.booking_date_time < datetime.now(),
        models.Booking.payment_status == 'prepayment_paid'
    ).all()

    # Фильтруем те, на которые еще нет отзыва
    result = []
    for booking in bookings:
        existing_review = db.query(models.Review).filter(
            models.Review.booking_id == booking.id
        ).first()
        if not existing_review:
            result.append(booking)

    return result


def create_review(db: Session, user_id: int, quest_id: int, booking_id: int,
                  rating: int, comment: str = None):
    """Создает отзыв на квест"""
    from datetime import datetime

    # Проверяем, может ли пользователь оставить отзыв
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == user_id,
        models.Booking.quest_id == quest_id
    ).first()

    if not booking:
        print(f"Booking not found: {booking_id}")
        return None

    # Проверяем, что квест уже прошел
    if booking.booking_date_time.replace(tzinfo=None) >= datetime.now():
        print(f"Quest not finished yet: {booking.booking_date_time}")
        return None

    # Проверяем, что предоплата внесена
    if booking.payment_status != 'prepayment_paid':
        print(f"Payment not paid: {booking.payment_status}")
        return None

    # Проверяем, нет ли уже отзыва
    existing = db.query(models.Review).filter(
        models.Review.booking_id == booking_id
    ).first()

    if existing:
        print(f"Review already exists for booking: {booking_id}")
        return None

    # Создаем отзыв
    review = models.Review(
        quest_id=quest_id,
        user_id=user_id,
        booking_id=booking_id,
        rating=rating,
        comment=comment
    )

    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_quest_reviews(db: Session, quest_id: int):
    """Получает все отзывы на квест"""

    return db.query(models.Review).filter(
        models.Review.quest_id == quest_id
    ).order_by(models.Review.created_at.desc()).all()


def get_quest_average_rating(db: Session, quest_id: int):
    """Получает средний рейтинг квеста"""

    from sqlalchemy import func

    result = db.query(func.avg(models.Review.rating)).filter(
        models.Review.quest_id == quest_id
    ).scalar()

    return round(result, 1) if result else None