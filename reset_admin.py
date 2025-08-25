from pymongo import MongoClient
import bcrypt


def ensure_admin(
    mongodb_uri: str = "mongodb://localhost:27017/ecommerce",
    username: str = "admin",
    email: str = "admin@example.com",
    new_password: str = "admin123",
) -> None:
    client = MongoClient(mongodb_uri)
    db = client.get_database()
    try:
        password_hash: bytes = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        result = db.users.update_one(
            {"$or": [{"username": username}, {"email": email}]},
            {
                "$set": {
                    "username": username,
                    "email": email,
                    "role": "admin",
                    "password_hash": password_hash,
                }
            },
            upsert=True,
        )

        if result.upserted_id is not None:
            print("Created admin user.")
        elif result.modified_count > 0:
            print("Updated existing admin user.")
        else:
            print("Admin already up to date.")

        doc = db.users.find_one({"username": username}, {"_id": 0, "email": 1, "username": 1, "role": 1})
        print("Admin doc:", doc)
        print("Temporary password set to:", new_password)
    finally:
        client.close()


if __name__ == "__main__":
    ensure_admin()


