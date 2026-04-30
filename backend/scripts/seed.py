from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.entities import Application, User


def run():
    db = SessionLocal()
    existing = db.query(User).filter(User.email == "admin@copilot.ai").first()
    if not existing:
        admin = User(
            email="admin@copilot.ai",
            full_name="Admin User",
            hashed_password=get_password_hash("AdminPass123!"),
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        db.add(
            Application(
                user_id=admin.id,
                company="Copilot Labs",
                role="AI Product Engineer",
                date_applied="2026-04-30",
                status="Interview",
                notes="First-round scheduled.",
            )
        )
        db.commit()
    db.close()


if __name__ == "__main__":
    run()
