from functools import wraps
from typing import List, Optional
from django.http import HttpRequest
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

class JWTAuthBearer(JWTAuth):
    """
    Bearer Authentication menggunakan JWT.
    Mewarisi langsung dari JWTAuth agar validasi token ditangani secara native.
    """
    def authenticate(self, request: HttpRequest, token: str) -> Optional[any]:
        try:
            user = super().authenticate(request, token)
            if user:
                # Memastikan akun user tersebut aktif (is_active=True)
                if not user.is_active:
                    raise HttpError(401, "Akun Anda telah dinonaktifkan.")
                
                # Menempelkan objek user ke request agar bisa dibaca middleware lain
                request.user = user
                return user
        except Exception:
            return None
        return None


def role_required(allowed_roles: List[str]):
    """
    Dekorator kustom Django Ninja untuk menyaring akses berdasarkan User.role.
    Aman digunakan pada endpoint dengan dependency injection.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Mencari objek HttpRequest secara dinamis di args maupun kwargs
            request = next((arg for arg in args if isinstance(arg, HttpRequest)), None)
            if not request:
                request = kwargs.get("request", None)

            # Validasi keberadaan user hasil login JWT
            if not request or not hasattr(request, "user") or not request.user.is_authenticated:
                raise HttpError(401, "Autentikasi diperlukan. Silakan login terlebih dahulu.")

            # Normalisasi pengecekan role menjadi uppercase demi konsistensi database
            user_role = getattr(request.user, "role", "").upper()
            allowed_roles_upper = [role.upper() for role in allowed_roles]

            # Bypass otomatis jika user adalah Superuser Django, atau cek role spesifik
            if not request.user.is_superuser and user_role not in allowed_roles_upper:
                raise HttpError(403, "Anda tidak memiliki hak akses untuk melakukan aksi ini.")

            return func(*args, **kwargs)
        return wrapper
    return decorator


# ==============================================================================
# 🌟 SHORTCUT ROLE DECORATORS (NEW)
# ==============================================================================

def is_admin(func):
    """Shortcut dekorator khusus untuk role ADMIN"""
    return role_required(['ADMIN'])(func)

def is_instructor(func):
    """Shortcut dekorator khusus untuk role INSTRUCTOR dan ADMIN"""
    return role_required(['INSTRUCTOR', 'ADMIN'])(func)

def is_student(func):
    """Shortcut dekorator khusus untuk role STUDENT"""
    return role_required(['STUDENT'])(func)