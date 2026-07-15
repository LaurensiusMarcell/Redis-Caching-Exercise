from pymongo import MongoClient
from django.conf import settings
from datetime import datetime

class MongoDBClient:
    def __init__(self):
        # Membaca URI dari settings, default ke local docker service name
        uri = getattr(settings, "MONGODB_URI", "mongodb://mongodb:27017/")
        self.client = MongoClient(uri)
        self.db = self.client["simple_lms"]
        self.activity_logs = self.db["activity_logs"]
        self.learning_analytics = self.db["learning_analytics"]

    def log_activity(self, user_id: int, username: str, action: str, details: dict):
        self.activity_logs.insert_one({
            "user_id": user_id,
            "username": username,
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow()
        })

    def log_analytics(self, student_id: int, course_id: int, lesson_id: int, quiz_score: float = 0.0, lessons_watched: int = 1):
        self.learning_analytics.insert_one({
            "student_id": student_id,
            "course_id": course_id,
            "lesson_id": lesson_id,
            "quiz_score": quiz_score,
            "lessons_watched": lessons_watched,
            "timestamp": datetime.utcnow()
        })

mongo_client = MongoDBClient()