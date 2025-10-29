from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal

class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="Hashed password")
    role: Literal['student','faculty','admin'] = Field('student', description="Role of the user")
    is_active: bool = Field(True, description="Is the user active")

class Course(BaseModel):
    title: str
    category: str
    level: Optional[str] = None
    description: Optional[str] = None

class ExamResult(BaseModel):
    user_email: EmailStr
    subject: str
    score: int
    total: int
