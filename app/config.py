import os

class Config:
    SECRET_KEY = os.environ.get('f40c6028ef7b18ac835f83c48477a132afef4e6d38b547c6') or 'dev-secret-key-change-in-production'
    
    #Configurare bd MySql
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://admin_englishmaster:1234@localhost/englishmaster'
        
        
    #Dezactiveaza tracking0ul modificarilor    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Setări sesiune
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'