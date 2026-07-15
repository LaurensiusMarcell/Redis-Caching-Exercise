import time
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from .models import Course

User = get_user_model()

@shared_task
def send_enrollment_email(user_id: int, course_title: str):
    """Memicu pengiriman email asinkronus saat siswa mendaftar kelas"""
    try:
        user = User.objects.get(id=user_id)
        # Di lingkungan produksi lokal, pesan ini akan tercetak di log Celery
        print(f"[CELERY TASK] Mengirim email welcome ke {user.email} untuk kelas {course_title}...")
        time.sleep(2) # Mensimulasikan jeda waktu pengiriman email jaringan
        return f"Email sukses dikirim ke {user.email}"
    except User.DoesNotExist:
        return "User tidak ditemukan"

@shared_task
def generate_certificate(user_id: int, course_id: int):
    """Memicu pembuatan file sertifikat kelulusan di background"""
    print(f"[CELERY TASK] Membuat sertifikat PDF untuk User ID {user_id} pada Course ID {course_id}...")
    time.sleep(3)
    return "Sertifikat berhasil dibuat"

@shared_task
def export_course_report(course_id: int, instructor_email: str):
    """Memicu kompilasi laporan performa kelas ke CSV/Excel"""
    print(f"[CELERY TASK] Mengekspor laporan untuk Course ID {course_id}, tujuan email: {instructor_email}...")
    time.sleep(4)
    return "Ekspor laporan selesai"

@shared_task
def update_course_statistics():
    """Scheduled Task yang dipicu berkala oleh Celery Beat tiap jam"""
    print("[CELERY BEAT] Memperbarui metrik analitik kelas ke MongoDB...")
    return "Statistik berhasil diperbarui"