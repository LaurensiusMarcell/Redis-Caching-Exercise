from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# ==============================================================================
# 🔐 AUTH & USER SCHEMAS
# ==============================================================================

class RegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(default="student", description="Pilihan: student, instructor, admin")


class UserOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str


class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=150)


# ==============================================================================
# 📚 COURSE & LESSON SCHEMAS
# ==============================================================================

class LessonOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order: int
    title: str
    content: str


class CourseOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    description: str
    instructor: UserOutSchema
    category_id: Optional[int] = None


class CourseCreateSchema(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(...)
    category_id: int


class CourseUpdateSchema(BaseModel):
    """Skema opsional khusus untuk pembaruan parsial (PATCH HTTP)"""
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None


# ==============================================================================
# 🎓 ENROLLMENT & PROGRESS SCHEMAS
# ==============================================================================

class EnrollmentCreateSchema(BaseModel):
    course_id: int


class EnrollmentOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course: CourseOutSchema
    enrolled_at: datetime
    progress_percentage: float = 0.0


class ProgressCreateSchema(BaseModel):
    lesson_id: int


# ==============================================================================
# ✉️ UTILITY / COMMON SCHEMAS
# ==============================================================================

class MessageSchema(BaseModel):
    """Skema standar untuk response berupa custom message/detail text"""
    message: str