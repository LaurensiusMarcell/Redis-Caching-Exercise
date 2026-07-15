from typing import List, Optional
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from ninja import Router, Query
from ninja.errors import HttpError

# Import dekorator spesifik baru
from .auth import JWTAuthBearer, is_admin, is_instructor, is_student
from .models import Category, Course, Enrollment, Lesson, Progress
from .schemas import (
    CourseCreateSchema,
    CourseOutSchema,
    CourseUpdateSchema,
    EnrollmentCreateSchema,
    EnrollmentOutSchema,
    RegisterSchema,
    UserOutSchema,
    UserUpdateSchema,
)

router = Router()
User = get_user_model()

# ==============================================================================
# 🔐 AUTHENTICATION & USER ENDPOINTS
# ==============================================================================

@router.post("/auth/register", response={201: UserOutSchema}, auth=None, tags=["JWT Authentication"])
def register(request, data: RegisterSchema):
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah terdaftar.")
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email sudah terdaftar.")
    
    role_choice = data.role.upper()
    valid_roles = [User.Role.ADMIN, User.Role.INSTRUCTOR, User.Role.STUDENT]
    if role_choice not in valid_roles:
        role_choice = User.Role.STUDENT

    user = User.objects.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        role=role_choice
    )
    return 201, user


@router.get("/auth/me", response=UserOutSchema, auth=JWTAuthBearer(), tags=["JWT Authentication"])
def get_me(request):
    return request.user


@router.put("/auth/me", response=UserOutSchema, auth=JWTAuthBearer(), tags=["JWT Authentication"])
def update_me(request, data: UserUpdateSchema):
    user = request.user
    
    for attr, value in data.model_dump(exclude_none=True).items():
        if attr == "username" and User.objects.exclude(id=user.id).filter(username=value).exists():
            raise HttpError(400, "Username ini sudah digunakan.")
        if attr == "email" and User.objects.exclude(id=user.id).filter(email=value).exists():
            raise HttpError(400, "Email ini sudah digunakan.")
        setattr(user, attr, value)
        
    user.save()
    return user


# ==============================================================================
# 📚 COURSES ENDPOINTS (PUBLIC & PROTECTED)
# ==============================================================================

@router.get("/courses", response=List[CourseOutSchema], auth=None, tags=["Courses"])
def list_courses(
    request, 
    search: Optional[str] = None, 
    page: int = Query(1, ge=1), 
    limit: int = Query(10, ge=1, le=100)
):
    queryset = Course.objects.select_related('instructor', 'category').all()
    if search:
        queryset = queryset.filter(title__icontains=search)
    
    start = (page - 1) * limit
    end = start + limit
    return list(queryset[start:end])


@router.get("/courses/{id}", response=CourseOutSchema, auth=None, tags=["Courses"])
def get_course_detail(request, id: int):
    return get_object_or_404(Course.objects.select_related('instructor'), id=id)


@router.post("/courses", response={201: CourseOutSchema}, auth=JWTAuthBearer(), tags=["Courses"])
@is_instructor
def create_course(request, data: CourseCreateSchema):
    category = get_object_or_404(Category, id=data.category_id)
    
    course_slug = slugify(data.title)
    if Course.objects.filter(slug=course_slug).exists():
        course_slug = f"{course_slug}-{Course.objects.count() + 1}"

    course = Course.objects.create(
        title=data.title,
        slug=course_slug,
        description=data.description,
        instructor=request.user,
        category=category
    )
    return 201, course


@router.patch("/courses/{id}", response=CourseOutSchema, auth=JWTAuthBearer(), tags=["Courses"])
@is_instructor
def update_course(request, id: int, data: CourseUpdateSchema):
    course = get_object_or_404(Course, id=id)
    
    # 🛡️ Ownership Validation: Hanya Owner atau Admin yang boleh mengedit
    if request.user.role != 'ADMIN' and course.instructor != request.user:
        raise HttpError(403, "Akses ditolak. Anda bukan pemilik (instructor) resmi dari kelas ini.")
    
    update_data = data.model_dump(exclude_none=True)
    
    if 'category_id' in update_data:
        category = get_object_or_404(Category, id=update_data.pop('category_id'))
        course.category = category
        
    for attr, value in update_data.items():
        setattr(course, attr, value)
        if attr == 'title':
            course.slug = slugify(value)
            
    course.save()
    return course


@router.delete("/courses/{id}", response={204: None}, auth=JWTAuthBearer(), tags=["Courses"])
@is_admin
def delete_course(request, id: int):
    course = get_object_or_404(Course, id=id)
    course.delete()
    return 204, None


# ==============================================================================
# 🎓 ENROLLMENTS & PROGRESS ENDPOINTS
# ==============================================================================

@router.post("/enrollments", response={201: dict}, auth=JWTAuthBearer(), tags=["Enrollments"])
@is_student
def enroll_course(request, data: EnrollmentCreateSchema):
    course = get_object_or_404(Course, id=data.course_id)
    try:
        Enrollment.objects.create(student=request.user, course=course)
        return 201, {"message": f"Sukses terdaftar di kelas {course.title}"}
    except IntegrityError:
        raise HttpError(400, "Anda sudah mengambil kelas ini sebelumnya.")


@router.get("/enrollments/my-courses", response=List[EnrollmentOutSchema], auth=JWTAuthBearer(), tags=["Enrollments"])
@is_student
def my_courses(request):
    queryset = Enrollment.objects.filter(student=request.user).select_related('course', 'course__instructor')
    return list(queryset)


@router.post("/enrollments/{id}/progress", response={200: dict}, auth=JWTAuthBearer(), tags=["Enrollments"])
@is_student
def mark_lesson_complete(request, id: int, lesson_id: int):
    enrollment = get_object_or_404(Enrollment, id=id, student=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=enrollment.course)
    
    progress, created = Progress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
        defaults={'is_completed': True}
    )
    if not created and not progress.is_completed:
        progress.is_completed = True
        progress.save()
        
    return 200, {"message": f"Materi '{lesson.title}' berhasil diselesaikan!"}