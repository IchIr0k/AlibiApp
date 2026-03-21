from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Date, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    bookings = relationship("Booking", back_populates="user")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Quest(Base):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    genre = Column(String(50), nullable=False)
    difficulty = Column(String(30), nullable=False)
    duration_minutes = Column(Integer, default=60)
    fear_level = Column(Integer, nullable=False)
    min_players = Column(Integer, nullable=False, default=2)
    max_players = Column(Integer, nullable=False, default=6)
    address = Column(String(255), nullable=False, default="Адрес не указан")
    image_path = Column(String(255))
    price = Column(Integer, default=2000)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    schedules = relationship("Schedule", back_populates="quest", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="quest")
    reviews = relationship("Review", back_populates="quest", cascade="all, delete-orphan")


class BookingStatus(Base):
    __tablename__ = "booking_statuses"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(20), default='#6c757d')

    bookings = relationship("Booking", back_populates="status")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    quest_id = Column(Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False)
    schedule_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    max_slots = Column(Integer, default=1)
    booked_slots = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    quest = relationship("Quest", back_populates="schedules")
    bookings = relationship("Booking", back_populates="schedule")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    quest_id = Column(Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="SET NULL"))
    status_id = Column(Integer, ForeignKey("booking_statuses.id"), default=1)

    booking_date_time = Column(DateTime(timezone=True), nullable=False)
    participants_count = Column(Integer, nullable=False, default=2)
    total_price = Column(Integer, nullable=False, default=2000)
    prepayment = Column(Integer, nullable=False, default=0)
    payment_method = Column(String(50), nullable=False, default='card')
    payment_status = Column(String(30), default='prepayment_pending')
    customer_name = Column(String(200), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(120))
    special_requests = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="bookings")
    quest = relationship("Quest", back_populates="bookings")
    schedule = relationship("Schedule", back_populates="bookings")
    status = relationship("BookingStatus", back_populates="bookings")
    review = relationship("Review", back_populates="booking", uselist=False, cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    quest_id = Column(Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    quest = relationship("Quest", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    booking = relationship("Booking", back_populates="review")


class QuestReview(Base):
    __tablename__ = "quest_reviews"

    id = Column(Integer, primary_key=True, index=True)
    quest_id = Column(Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="SET NULL"), unique=True)

    rating = Column(Integer, nullable=False)
    review_text = Column(Text)
    difficulty_rating = Column(Integer)
    fear_rating = Column(Integer)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    quest = relationship("Quest", back_populates="reviews_old")
    user = relationship("User", back_populates="reviews_old")
    booking = relationship("Booking", back_populates="review_old")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action_type = Column(String(50), nullable=False)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer)
    old_values = Column(Text)
    new_values = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    related_entity_type = Column(String(50))
    related_entity_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")


# Добавляем недостающие relationship в Quest и User
Quest.reviews_old = relationship("QuestReview", back_populates="quest", cascade="all, delete-orphan")
User.reviews_old = relationship("QuestReview", back_populates="user", cascade="all, delete-orphan")
Booking.review_old = relationship("QuestReview", back_populates="booking", uselist=False)