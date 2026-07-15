from ninja_extra import NinjaExtraAPI, api_controller, route
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.schema import TokenObtainPairInputSchema, TokenRefreshInputSchema, TokenVerifyInputSchema
from courses.api import router as courses_router

# Inisialisasi API utama
api = NinjaExtraAPI(
    title="Simple LMS API",
    version="1.0.0",
    description="API untuk platform Simple LMS menggunakan Django Ninja Extra dan JWT."
)

# Kustomisasi Rute JWT agar masuk ke kelompok "/api/auth/..." secara aman dan eksplisit
@api_controller('/auth', tags=['JWT Authentication'])
class CustomAuthController(NinjaJWTDefaultController):
    
    @route.post("/login", url_name="token_obtain")
    def obtain_token(self, user_token: TokenObtainPairInputSchema):
        return user_token.to_response()

    @route.post("/refresh", url_name="token_refresh")
    def refresh_token(self, refresh_token: TokenRefreshInputSchema):
        return refresh_token.to_response()

    @route.post("/verify", url_name="token_verify")
    def verify_token(self, verify_token: TokenVerifyInputSchema):
        return verify_token.to_response()


# 1. Daftarkan Controller JWT Kustom
api.register_controllers(CustomAuthController)

# 2. Daftarkan router dari aplikasi courses Anda
api.add_router("", courses_router)