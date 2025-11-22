from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(13), nullable=False)
    email = db.Column(db.String(255), unique = True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('user','professor', 'admin'), default='user', nullable=False)
    points = db.Column(db.Integer, default=0)
    premium = db.Column(db.Boolean, default=False)
    
    #Campuri pt profesori
    bio = db.Column(db.Text, nullable=True)
    specialization = db.Column(db.String(20),nullable=True)
    rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    # Relații
    meetings_as_student = db.relationship('Meeting', foreign_keys='Meeting.student_id', backref='student', lazy=True)
    meetings_as_professor = db.relationship('Meeting', foreign_keys='Meeting.professor_id', backref='professor', lazy=True)
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """Criptează și salvează parola"""
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Verifică dacă parola introdusă este corectă"""
        return bcrypt.check_password_hash(self.password, password)
    
    def get_full_name(self):
        """Returnează numele complet"""
        return f"{self.first_name} {self.last_name}"
    
    def can_request_feedback(self):
        """Verifică dacă utilizatorul poate solicita feedback (100+ puncte)"""
        return self.points >= 100
    
    def deduct_points_for_feedback(self):
        """Scade 100 puncte pentru feedback"""
        if self.points >= 100:
            self.points -= 100
            return True
        return False
    
    def to_dict(self):
        """Convertește obiectul la dicționar (pentru JSON)"""
        data = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'role': self.role,
            'points': self.points,
            'premium': self.premium,
            'created_at': self.created_at.isoformat()
        }
        
        # Adaugă info pentru profesori
        if self.role == 'professor':
            data.update({
                'bio': self.bio,
                'specialization': self.specialization,
                'rating': self.rating,
                'total_reviews': self.total_reviews,
                'is_available': self.is_available
            })
        
        return data


class Meeting(db.Model):
    __tablename__ = 'meetings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relații cu utilizatorii
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Detalii întâlnire
    meeting_date = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    
    # Status: pending, confirmed, rejected, completed, cancelled
    status = db.Column(db.Enum('pending', 'confirmed', 'rejected', 'completed', 'cancelled'), 
                      default='pending', nullable=False)
    
    # Mesaj de la student
    student_message = db.Column(db.Text, nullable=True)
    
    # Răspuns de la profesor
    professor_response = db.Column(db.Text, nullable=True)
    
    # Link pentru meeting online (opțional)
    # meeting_link = db.Column(db.String(500), nullable=True)
    
    # Puncte consumate pentru această întâlnire
    points_cost = db.Column(db.Integer, default=100)
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Meeting {self.id}: Student {self.student_id} - Professor {self.professor_id}>'
    
    def to_dict(self):
        """Convertește obiectul la dicționar (pentru JSON)"""
        return {
            'id': self.id,
            'student': {
                'id': self.student.id,
                'name': self.student.get_full_name(),
                'email': self.student.email
            },
            'professor': {
                'id': self.professor.id,
                'name': self.professor.get_full_name(),
                'email': self.professor.email,
                'specialization': self.professor.specialization,
                'rating': self.professor.rating
            },
            'meeting_date': self.meeting_date.isoformat(),
            'duration_minutes': self.duration_minutes,
            'status': self.status,
            'student_message': self.student_message,
            'professor_response': self.professor_response,
            'meeting_link': self.meeting_link,
            'points_cost': self.points_cost,
            'created_at': self.created_at.isoformat()
        }
    
    def can_cancel(self):
        """Verifică dacă întâlnirea poate fi anulată (doar pending/confirmed)"""
        return self.status in ['pending', 'confirmed']
    
    def is_upcoming(self):
        """Verifică dacă întâlnirea este viitoare"""
        return self.meeting_date > datetime.now(timezone.utc)
