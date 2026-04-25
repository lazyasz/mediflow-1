# ============================================================
# config.py — Application Configuration
# ============================================================

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mediflow-dev-secret-key-change-in-production')
    db_url = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(basedir, "mediflow.db")}')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'mediflow-jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = False  # Set True in production (HTTPS)
    JWT_COOKIE_CSRF_PROTECT = False  # Simplified for dev
    JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'

    # Queue Engine
    CONSULT_MINUTES_DEFAULT = 12
    QUEUE_REBALANCE_INTERVAL = 60  # seconds
    MAX_ADVANCE_BOOKING_DAYS = 30
    SLOT_DURATION_MINUTES = 30
    WORK_START_HOUR = 9
    WORK_END_HOUR = 17


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_CSRF_PROTECT = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
