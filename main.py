import os
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from database import db, create_document, get_documents
from schemas import User, Course

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def ensure_default_users():
    if db is None:
        return
    users = db["user"]
    defaults = [
        {
            "name": "Admin",
            "email": "admin@elearning.com",
            "password_hash": hash_password("admin123"),
            "role": "admin",
            "is_active": True,
        },
        {
            "name": "Faculty",
            "email": "faculty@elearning.com",
            "password_hash": hash_password("faculty123"),
            "role": "faculty",
            "is_active": True,
        },
    ]
    for u in defaults:
        if not users.find_one({"email": u["email"]}):
            users.insert_one(u)


def seed_samples():
    if db is None:
        return
    courses = db["course"]
    if courses.count_documents({}) == 0:
        samples = [
            {"title": "Web Development", "category": "Courses", "level": "Beginner"},
            {"title": "Cyber Security", "category": "Courses", "level": "Intermediate"},
            {"title": "Python", "category": "Programming Languages", "level": "Beginner"},
            {"title": "C++", "category": "Programming Languages", "level": "Intermediate"},
        ]
        courses.insert_many(samples)


@app.on_event("startup")
async def startup_event():
    try:
        ensure_default_users()
        seed_samples()
    except Exception:
        pass


# Schemas for requests
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    name: str
    email: EmailStr
    role: str
    token: str


@app.post("/auth/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    users = db["user"]
    if users.find_one({"email": req.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=req.name,
        email=req.email,
        password_hash=hash_password(req.password),
        role="student",
        is_active=True,
    )
    create_document("user", user)
    token = hash_password(req.email + "|" + req.password)
    return AuthResponse(name=user.name, email=user.email, role=user.role, token=token)


@app.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    users = db["user"]
    found = users.find_one({"email": req.email})
    if not found:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if found.get("password_hash") != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = hash_password(req.email + "|" + req.password)
    return AuthResponse(name=found.get("name"), email=found.get("email"), role=found.get("role", "student"), token=token)


@app.get("/courses")
def list_courses():
    try:
        items = get_documents("course")
        # convert ObjectId to string if present
        for it in items:
            if "_id" in it:
                it["id"] = str(it.pop("_id"))
        return {"items": items}
    except Exception as e:
        return {"items": [], "error": str(e)}


@app.get("/")
def read_root():
    return {"message": "eLearning backend running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
