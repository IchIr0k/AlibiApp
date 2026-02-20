from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()

try:
    # Проверяем расписание
    schedules = db.query(models.Schedule).filter(
        models.Schedule.schedule_date >= datetime.now().date()
    ).all()

    print(f"Найдено слотов в расписании: {len(schedules)}")

    for s in schedules[:10]:  # Покажем первые 10
        print(f"\nID: {s.id}")
        print(f"Квест ID: {s.quest_id}")
        print(f"Дата: {s.schedule_date}")
        print(f"Время: {s.start_time} - {s.end_time}")
        print(f"Занято слотов: {s.booked_slots}/{s.max_slots}")
        print(f"Доступно: {s.is_available}")
        print("-" * 30)

except Exception as e:
    print(f"Ошибка: {e}")
finally:
    db.close()