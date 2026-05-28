import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-insecure-key-changer-en-prod'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///ticketsecure.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False   # True en prod (HTTPS obligatoire)
    SESSION_COOKIE_SAMESITE = 'Strict'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

    RATELIMIT_STORAGE_URL = 'memory://'

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 1025))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@ticketsecure.local')

    MAX_TICKETS_PAR_SPECTACLE = 4
    MAX_TENTATIVES_CONNEXION = 5
    DUREE_VERROUILLAGE_MINUTES = 15
    EXPIRATION_TOKEN_MINUTES = 30


class DevelopmentConfig(Config):
    DEBUG = True


class ServerConfig(Config):
    # SQLite + DEBUG=False : pour déploiement sans MySQL (serveur école)
    # Pas de SESSION_COOKIE_SECURE car pas de HTTPS obligatoire
    DEBUG = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    # DATABASE_URL doit pointer vers MySQL en prod
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


config = {
    'development': DevelopmentConfig,
    'server':      ServerConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}