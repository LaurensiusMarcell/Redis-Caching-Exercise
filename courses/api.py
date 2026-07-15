from typing import List, Optional
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
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
    MessageSchema
)

# Integrasi MongoDB Client & Celery Tasks
from .mongodb import mongo_client
from .tasks import send_enrollment_email, generate_certificate, export_course_report

router = Router()
User = get_user_model()

CACHE_KEY_COURSES_LIST = "courses:list"
CACHE_KEY_COURSE_DETAIL = "courses:detail:{id}"

# Helper untuk menangani implementasi ratelimit pada Django Ninja
def rate_limit_guard(request):
    # django-ratelimit menaruh flag 'limited' pada request objek
    if getattr(request, 'limited', False):
        raise HttpError(429, "Terlalu banyak permintaan. Batas Anda adalah 60 request/menit.")

# ==============================================================================
# 🔐 AUTHENTICATION & USER ENDPOINTS
# ==============================================================================

@router.post("/auth/register", response={201: UserOutSchema}, auth=None, tags=["JWT Authentication"])
@ratelimit(key='ip', rate='60/m', block=False)
def register(request, data: RegisterSchema):
    rate_limit_guard(request)
    
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
    
    mongo_client.log_activity(user.id, user.username, "USER_REGISTER", {"role": role_choice})
    return 201, user


@router.get("/auth/me", response=UserOutSchema, auth=JWTAuthBearer(), tags=["JWT Authentication"])
@ratelimit(key='ip', rate='60/m', block=False)
def get_me(request):
    rate_limit_guard(request)
    return request.user


@router.put("/auth/me", response=UserOutSchema, auth=JWTAuthBearer(), tags=["JWT Authentication"])
@ratelimit(key='ip', rate='60/m', block=False)
def update_me(request, data: UserUpdateSchema):
    rate_limit_guard(request)
    user = request.user
    
    for attr, value in data.model_dump(exclude_none=True).items():
        if attr == "username" and User.objects.exclude(id=user.id).filter(username=value).exists():
            raise HttpError(400, "Username ini sudah digunakan.")
        if attr == "email" and User.objects.exclude(id=user.id).filter(email=value).exists():
            raise HttpError(400, "Email ini sudah digunakan.")
        setattr(user, attr, value)
        
    user.save()
    mongo_client.log_activity(user.id, user.username, "USER_UPDATE_PROFILE", {})
    return user


# ==============================================================================
# 📚 COURSES ENDPOINTS (PUBLIC & PROTECTED)
# ==============================================================================

@router.get("/courses", response=List[CourseOutSchema], auth=None, tags=["Courses"])
@ratelimit(key='ip', rate='60/m', block=False)
def list_courses(
    request, 
    search: Optional[str] = None, 
    page: int = Query(1, ge=1), 
    limit: int = Query(10, ge=1, le=100)
):
    rate_limit_guard(request)
    
    # Jika ada pencarian spesifik, bypass cache agar data real-time
    if search:
        queryset = Course.objects.select_related('instructor', 'category').filter(title__icontains=search)
        start = (page - 1) * limit
        return list(queryset[start:start+limit])
        
    # ⚡ Redis Cache Strategy untuk Pagination List
    cache_key = f"{CACHE_KEY_COURSES_LIST}:page_{page}:limit_{limit}"
    cached_list = cache.get(cache_key)
    if cached_list:
        return cached_list

    queryset = Course.objects.select_related('instructor', 'category').all()
    start = (page - 1) * limit
    data = list(queryset[start:start+limit])
    
    cache.set(cache_key, data, timeout=600)  # Simpan cache selama 10 menit
    return data


@router.get("/courses/{id}", response=CourseOutSchema, auth=None, tags=["Courses"])
@ratelimit(key='ip', rate='60/m', block=False)
def get_course_detail(request, id: int):
    rate_limit_guard(request)
    
    # ⚡ Redis Cache Strategy untuk Detail Object
    cache_key = CACHE_KEY_COURSE_DETAIL.format(id=id)
    cached_course = cache.get(cache_key)
    if cached_course:
        return cached_course

    course = get_object_or_404(Course.objects.select_related('instructor'), id=id)
    cache.set(cache_key, course, timeout=1200)  # Simpan cache selama 20 menit
    return course


@router.post("/courses", response={201: CourseOutSchema}, auth=JWTAuthBearer(), tags=["Courses"])
@is_instructor
@ratelimit(key='user', rate='60/m', block=False)
def create_course(request, data: CourseCreateSchema):
    rate_limit_guard(request)
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
    
    # 🔄 Invalidation: Bersihkan cache list saat ada item baru
    cache.delete_pattern(f"{CACHE_KEY_COURSES_LIST}:*")
    mongo_client.log_activity(request.user.id, request.user.username, "COURSE_CREATION", {"course_id": course.id})
    
    return 201, course


@router.patch("/courses/{id}", response=CourseOutSchema, auth=JWTAuthBearer(), tags=["Courses"])
@is_instructor
def update_course(request, id: int, data: CourseUpdateSchema):
    course = get_object_or_404(Course, id=id)
    
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

    # 🔄 Invalidation: Hapus cache item ini dan seluruh list pagination
    cache.delete(CACHE_KEY_COURSE_DETAIL.format(id=id))
    cache.delete_pattern(f"{CACHE_KEY_COURSES_LIST}:*")
    
    mongo_client.log_activity(request.user.id, request.user.username, "COURSE_UPDATE", {"course_id": course.id})
    return course


@router.delete("/courses/{id}", response={204: None}, auth=JWTAuthBearer(), tags=["Courses"])
@is_admin
def delete_course(request, id: int):
    course = get_object_or_404(Course, id=id)
    course.delete()

    # 🔄 Invalidation
    cache.delete(CACHE_KEY_COURSE_DETAIL.format(id=id))
    cache.delete_pattern(f"{CACHE_KEY_COURSES_LIST}:*")
    
    mongo_client.log_activity(request.user.id, request.user.username, "COURSE_DELETION", {"course_id": id})
    return 204, None


# ==============================================================================
# 🎓 ENROLLMENTS & PROGRESS ENDPOINTS
# ==============================================================================

@router.post("/enrollments", response={201: MessageSchema}, auth=JWTAuthBearer(), tags=["Enrollments"])
@is_student
def enroll_course(request, data: EnrollmentCreateSchema):
    course = get_object_or_404(Course, id=data.course_id)
    try:
        Enrollment.objects.create(student=request.user, course=course)
        
        # 📇 Picu Asynchronous Task Celery untuk Mengirim Email Welcome
        send_enrollment_email.delay(request.user.id, course.title)
        
        mongo_client.log_activity(request.user.id, request.user.username, "COURSE_ENROLL", {"course_id": course.id})
        return 201, {"message": f"Sukses terdaftar di kelas {course.title}"}
    except IntegrityError:
        raise HttpError(400, "Anda sudah mengambil kelas ini sebelumnya.")


@router.get("/enrollments/my-courses", response=List[EnrollmentOutSchema], auth=JWTAuthBearer(), tags=["Enrollments"])
@is_student
def my_courses(request):
    queryset = Enrollment.objects.filter(student=request.user).select_related('course', 'course__instructor')
    return list(queryset)


@router.post("/enrollments/{id}/progress", response={200: MessageSchema}, auth=JWTAuthBearer(), tags=["Enrollments"])
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
        
    # 🍃 Catat data ke MongoDB Learning Analytics
    mongo_client.log_analytics(request.user.id, enrollment.course.id, lesson_id)
    
    # 📇 Cek otomatisasi progress untuk trigger sertifikat (Celery Task)
    # Jika progress sudah mencapai 100% (contoh logika sederhana evaluasi)
    if enrollment.progress_percentage >= 100.0:
        generate_certificate.delay(request.user.id, enrollment.course.id)

    return 200, {"message": f"Materi '{lesson.title}' berhasil diselesaikan!"}


@router.post("/courses/{id}/export-report", response={202: MessageSchema}, auth=JWTAuthBearer(), tags=["Courses"])
@is_instructor
def request_course_report(request, id: int):
    """Endpoint baru untuk memicu Async Task Export CSV Report via Celery"""
    course = get_object_or_404(Course, id=id)
    if request.user.role != 'ADMIN' and course.instructor != request.user:
        raise HttpError(403, "Akses ditolak.")
        
    export_course_report.delay(course.id, request.user.email)
    return 202, {"message": "Proses ekspor laporan sedang berjalan di background, silakan periksa email Anda beberapa saat lagi."}