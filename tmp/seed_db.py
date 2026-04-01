from app.db.database import SessionLocal
from app.db.models import Client
from app.core.security import hash_api_key
from app.core.config import settings

def seed_client():
    db = SessionLocal()
    key = settings.GROQ_API_KEY
    if not key:
        print("No GROQ_API_KEY found in settings.")
        return
    
    hashed = hash_api_key(key)
    existing = db.query(Client).filter(Client.api_key_hash == hashed).first()
    if not existing:
        client = Client(
            organization_name="AutoSeed-Local",
            api_key_hash=hashed,
            tier="premium",
            is_active=True
        )
        db.add(client)
        db.commit()
        print(f"Successfully seeded Client with hashed Groq key: {hashed}")
    else:
        print("Client already exists in DB with this key hash.")
    db.close()

if __name__ == "__main__":
    seed_client()
