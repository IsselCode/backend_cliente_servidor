from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    TECHNICIAN = "technician"
    QUALITY = "quality"
