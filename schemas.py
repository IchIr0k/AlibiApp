from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    phone: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)


class QuestBase(BaseModel):
    title: str
    description: str
    genre: str
    difficulty: str
    fear_level: int
    min_players: int
    max_players: int
    price: int
    organizer_email: str

    model_config = ConfigDict(from_attributes=True)


class QuestCreate(QuestBase):
    pass


class QuestOut(QuestBase):
    id: int
    image_path: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    quest_id: int
    date: str
    timeslot: str

    model_config = ConfigDict(from_attributes=True)


class BookingOut(BaseModel):
    id: int
    user_id: int
    quest_id: int
    booking_date_time: datetime
    total_price: int
    customer_name: str
    customer_phone: str
    payment_status: str

    model_config = ConfigDict(from_attributes=True)