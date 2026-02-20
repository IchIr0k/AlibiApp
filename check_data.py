from database import SessionLocal
import models

db = SessionLocal()

try:
    # Проверяем квесты
    quests = db.query(models.Quest).filter(models.Quest.is_active == True).all()
    print(f"Найдено квестов: {len(quests)}")

    for quest in quests:
        print(f"\nID: {quest.id}")
        print(f"Название: {quest.title}")
        print(f"Описание: {quest.description[:50]}...")
        print(f"Жанр: {quest.genre}")
        print(f"Сложность: {quest.difficulty}")
        print(f"Цена: {quest.price}")
        print(f"Изображение: {quest.image_path}")
        print("-" * 30)

except Exception as e:
    print(f"Ошибка: {e}")
finally:
    db.close()