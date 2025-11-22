from flask import Flask
from flask_login import LoginManager
from app.config import Config
from app.models import db, bcrypt, User

# Inițializare Login Manager
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app():
    # Creează aplicația Flask
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inițializează extensiile
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Te rugăm să te autentifici pentru a accesa această pagină.'
    
    # Creează tabelele în baza de date
    with app.app_context():
        db.create_all()
        print("✅ Baza de date inițializată cu succes!")
    
    # Înregistrează rutele
    from app.routes import main
    app.register_blueprint(main)
    
    return app