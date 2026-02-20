from database import SessionLocal
import models

db = SessionLocal()

try:
    # Проверяем все квесты, включая неактивные
    all_quests = db.query(models.Quest).all()
    print(f"Всего квестов в БД: {len(all_quests)}")

    for quest in all_quests:
        print(f"\nID: {quest.id}")
        print(f"Название: {quest.title}")
        print(f"is_active: {quest.is_active}")
        print(f"Описание: {quest.description[:50]}...")
        print("-" * 30)

    # Проверяем только активные квесты
    active_quests = db.query(models.Quest).filter(models.Quest.is_active == True).all()
    print(f"\nАктивных квестов: {len(active_quests)}")

    for quest in active_quests:
        print(f"ID: {quest.id} - {quest.title}")

except Exception as e:
    print(f"Ошибка: {e}")
finally:
    db.close()