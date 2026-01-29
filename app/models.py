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
    last_name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255), unique = True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('user','professor', 'admin'), default='user', nullable=False)
    points = db.Column(db.Integer, default=0)
    premium = db.Column(db.Boolean, default=False)
    
    #Campuri pt profesori
    bio = db.Column(db.Text, nullable=True)
    specialization = db.Column(db.String(500),nullable=True)
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
        """Verifică dacă utilizatorul poate solicita feedback (500+ puncte)"""
        return self.points >= 500
    
    def deduct_points_for_feedback(self):
        """Scade 500 puncte pentru feedback"""
        if self.points >= 500:
            self.points -= 500
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

class Lesson(db.Model):
    __tablename__ = 'lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    level = db.Column(db.Enum('beginner', 'intermediate', 'advanced'), nullable=False, index=True)
    category = db.Column(db.String(100),nullable=True) #Grammar, Vocabulary, Reading
    # Profesorul care a creat lectia
    professor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) 
    # Durata estimata (minute)
    duration_minutes = db.Column(db.Integer, default=30)  
    # Dificultatea (1-5)
    difficulty = db.Column(db.Integer, default=3)
    # Rating si statistici
    rating = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    completions = db.Column(db.Integer, default=0)
    
    # Status: draft, published, archived
    status = db.Column(db.Enum('draft','published','archived'), default='published', nullable=False)
    # URL imagine pentru preview
    image_url = db.Column(db.String(500), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relatie cu profesorul
    professor = db.relationship('User', backref='lessons')
    
    def __repr__(self):
        return f'<Lesson {self.title}>'
    
    def get_level_display(self):
        """Returneaza nivelul in format vizibil"""
        levels = {
            'beginner': 'Începător',
            'intermediate': 'Intermediar',
            'advanced': 'Avansat'
        }
        return levels.get(self.level, self.level)
    
    def get_difficulty_stars(self):
        """Returneaza dificultatea ca nr. de stele"""
        return '⭐' * self.difficulty
    
    def increment_views(self):
        self.views += 1
        db.session.commit()
    
    def calculate_completion_rate(self):
        """Calculeaza rata de finalizare"""
        if self.views == 0:
            return 0
        return round((self.completions / self.views) * 100, 1)
    
    def to_dict(self):
        """Convertire obiect la dictionar(pt JSON)"""
        return{
         'id': self.id,
            'title': self.title,
            'description': self.description,
            'content': self.content,
            'level': self.level,
            'level_display': self.get_level_display(),
            'category': self.category,
            'duration_minutes': self.duration_minutes,
            'difficulty': self.difficulty,
            'difficulty_stars': self.get_difficulty_stars(),
            'rating': self.rating,
            'total_ratings': self.total_ratings,
            'views': self.views,
            'completions': self.completions,
            'completion_rate': self.calculate_completion_rate(),
            'status': self.status,
            'image_url': self.image_url,
            'professor': {
                'id': self.professor.id,
                'name': self.professor.get_full_name(),
                'specialization': self.professor.specialization
            } if self.professor else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
     

class Meeting(db.Model):
    __tablename__ = 'meetings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relații cu utilizatorii
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Detalii întâlnire
    meeting_date = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    
    status = db.Column(db.Enum('pending', 'confirmed', 'rejected', 'completed', 'cancelled'), 
                      default='pending', nullable=False)
    
    student_message = db.Column(db.Text, nullable=True)
    
    professor_response = db.Column(db.Text, nullable=True)
    
    # Link pentru meeting online (opțional)
    meeting_link = db.Column(db.String(500), nullable=True)
    
    # Puncte consumate pentru această întâlnire
    points_cost = db.Column(db.Integer, default=500)
    
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

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Lecția asociată
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    passing_score = db.Column(db.Integer, default=70)  # Scor minim pentru trecere (%)
    time_limit_minutes = db.Column(db.Integer, nullable=True)  # Timp limită (opțional)
    max_attempts = db.Column(db.Integer, default=3)  # Număr maxim de încercări
    
    # Puncte acordate
    points_reward = db.Column(db.Integer, default=50)  # Puncte pentru trecere
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relații
    lesson = db.relationship('Lesson', backref='quizzes')
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('QuizSubmission', backref='quiz', lazy=True)
    
    def __repr__(self):
        return f'<Quiz {self.title}>'
    
    def to_dict(self, include_questions=False):
        """Convertește la dicționar"""
        data = {
            'id': self.id,
            'lesson_id': self.lesson_id,
            'title': self.title,
            'description': self.description,
            'passing_score': self.passing_score,
            'time_limit_minutes': self.time_limit_minutes,
            'max_attempts': self.max_attempts,
            'points_reward': self.points_reward,
            'total_questions': len(self.questions)
        }
        
        if include_questions:
            data['questions'] = [q.to_dict() for q in self.questions]
        
        return data


class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    
    # Conținut
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum('multiple_choice', 'true_false'), default='multiple_choice', nullable=False)
    
    # Răspunsuri (pentru multiple choice)
    option_a = db.Column(db.String(500), nullable=True)
    option_b = db.Column(db.String(500), nullable=True)
    option_c = db.Column(db.String(500), nullable=True)
    option_d = db.Column(db.String(500), nullable=True)
    
    correct_answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', 'D', sau 'T', 'F'
    
    explanation = db.Column(db.Text, nullable=True)
    
    # Puncte pt această întrebare
    points = db.Column(db.Integer, default=10)
    
    # Ordinea în quiz
    order = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Question {self.id}>'
    
    def to_dict(self, include_correct_answer=False):
        """Convertește la dicționar"""
        data = {
            'id': self.id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'points': self.points,
            'order': self.order
        }
        
        if self.question_type == 'multiple_choice':
            data['options'] = {
                'A': self.option_a,
                'B': self.option_b,
                'C': self.option_c,
                'D': self.option_d
            }
        
        if include_correct_answer:
            data['correct_answer'] = self.correct_answer
            data['explanation'] = self.explanation
        
        return data


class QuizSubmission(db.Model):
    __tablename__ = 'quiz_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relații
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    
    # Răspunsuri in format JSON {"1": "A", "2": "B", ...}
    answers = db.Column(db.Text, nullable=False)
    
    # Rezultate
    score = db.Column(db.Float, nullable=False)  # Scor procentual (0-100)
    points_earned = db.Column(db.Integer, default=0)  # Puncte câștigate
    
    # Status
    passed = db.Column(db.Boolean, default=False)
    
    # Timp
    time_taken_seconds = db.Column(db.Integer, nullable=True)
    
    # Încercare
    attempt_number = db.Column(db.Integer, default=1)
    
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relații
    user = db.relationship('User', backref='quiz_submissions')
    lesson = db.relationship('Lesson', backref='quiz_submissions')
    
    def __repr__(self):
        return f'<QuizSubmission user={self.user_id} quiz={self.quiz_id} score={self.score}>'
    
    def to_dict(self):
        """Convertește la dicționar"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'quiz_id': self.quiz_id,
            'lesson_id': self.lesson_id,
            'score': self.score,
            'points_earned': self.points_earned,
            'passed': self.passed,
            'time_taken_seconds': self.time_taken_seconds,
            'attempt_number': self.attempt_number,
            'submitted_at': self.submitted_at.isoformat()
        }


class Badge(db.Model):
    __tablename__ = 'badges'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Info badge
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(10), default='🏆')  # Emoji sau URL imagine
    
    # Criteriu de obținere
    criteria_type = db.Column(db.Enum('points', 'lessons_completed', 'streak', 'perfect_score', 'speed'), nullable=False)
    criteria_value = db.Column(db.Integer, nullable=False)
    
    # Nivel
    level = db.Column(db.Enum('bronze', 'silver', 'gold', 'platinum'), default='bronze')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Badge {self.name}>'
    
    def to_dict(self):
        """Convertește la dicționar"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'criteria_type': self.criteria_type,
            'criteria_value': self.criteria_value,
            'level': self.level
        }


class UserBadge(db.Model):
    __tablename__ = 'user_badges'
    
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id'), nullable=False)
    
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relații
    user = db.relationship('User', backref='user_badges')
    badge = db.relationship('Badge', backref='user_badges')
    
    def __repr__(self):
        return f'<UserBadge user={self.user_id} badge={self.badge_id}>'


class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    
    # Status
    status = db.Column(db.Enum('not_started', 'in_progress', 'completed'), default='not_started')
    
    # Progres (0-100%)
    progress_percentage = db.Column(db.Integer, default=0)
    
    # Încercări quiz
    quiz_attempts = db.Column(db.Integer, default=0)
    best_score = db.Column(db.Float, default=0.0)
    
    # Timp petrecut (secunde)
    time_spent_seconds = db.Column(db.Integer, default=0)
    
    # Timestamps
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relații
    user = db.relationship('User', backref='progress')
    lesson = db.relationship('Lesson', backref='user_progress')
    
    # Index unic pentru user + lesson
    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson'),)
    
    def __repr__(self):
        return f'<UserProgress user={self.user_id} lesson={self.lesson_id}>'
    
    def to_dict(self):
        """Convertește la dicționar"""
        return {
            'lesson_id': self.lesson_id,
            'lesson_title': self.lesson.title if self.lesson else None,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'quiz_attempts': self.quiz_attempts,
            'best_score': self.best_score,
            'time_spent_seconds': self.time_spent_seconds,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_accessed': self.last_accessed.isoformat()
        }

class Reward(db.Model):
    __tablename__ = 'rewards'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Utilizatorul care primește recompensa
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Tip recompensă: bonus_points, free_feedback, premium_trial
    reward_type = db.Column(db.Enum('bonus_points', 'free_feedback', 'premium_trial'), nullable=False)
    
    # Valoare (ex: număr puncte bonus)
    value = db.Column(db.Integer, default=0)
    
    # Descriere
    description = db.Column(db.Text, nullable=False)
    
    # Status: pending, claimed, expired
    status = db.Column(db.Enum('pending', 'claimed', 'expired'), default='pending')
    
    # Când a fost câștigată
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Când a fost revendicată
    claimed_at = db.Column(db.DateTime, nullable=True)
    
    # Data expirării
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relație
    user = db.relationship('User', backref='rewards')
    
    def __repr__(self):
        return f'<Reward {self.reward_type} for user {self.user_id}>'
    
    def is_expired(self):
        """Verifică dacă recompensa a expirat"""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False
    
    def claim(self):
        """Revendică recompensa"""
        if self.status == 'pending' and not self.is_expired():
            self.status = 'claimed'
            self.claimed_at = datetime.utcnow()
            return True
        return False
    
    def to_dict(self):
        """Convertește la dicționar"""
        return {
            'id': self.id,
            'reward_type': self.reward_type,
            'value': self.value,
            'description': self.description,
            'status': self.status,
            'earned_at': self.earned_at.isoformat(),
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired()
        }


# ==================== SPRINT 5: CLASE & FEEDBACK ====================

class Class(db.Model):
    """Model pentru clase create de profesori"""
    __tablename__ = 'classes'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Profesor care a creat clasa
    professor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Nume și descriere
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # Cod pentru a se alătura clasa
    
    # Status
    status = db.Column(db.Enum('active', 'archived'), default='active')
    
    # Dată creării
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relații
    professor = db.relationship('User', backref='classes_created')
    students = db.relationship('ClassStudent', backref='class_ref', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Class {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'code': self.code,
            'professor_id': self.professor_id,
            'professor_name': self.professor.get_full_name(),
            'student_count': len(self.students),
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }


class ClassStudent(db.Model):
    """Model pentru studenți înscriși în clase"""
    __tablename__ = 'class_students'
    
    id = db.Column(db.Integer, primary_key=True)
    
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dată înscrierii
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Progres în clasă
    progress_percentage = db.Column(db.Float, default=0.0)
    
    # Relații
    student = db.relationship('User', backref='class_enrollments')
    
    __table_args__ = (db.UniqueConstraint('class_id', 'student_id', name='unique_class_student'),)
    
    def __repr__(self):
        return f'<ClassStudent class_id={self.class_id} student_id={self.student_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'class_id': self.class_id,
            'student_id': self.student_id,
            'student_name': self.student.get_full_name(),
            'student_email': self.student.email,
            'student_points': self.student.points,
            'progress_percentage': self.progress_percentage,
            'joined_at': self.joined_at.isoformat()
        }


class Feedback(db.Model):
    """Model pentru feedback-ul profesorilor către studenți"""
    __tablename__ = 'feedbacks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relaționări
    professor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    quiz_submission_id = db.Column(db.Integer, db.ForeignKey('quiz_submissions.id'), nullable=True)
    
    # Conținut
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    
    # Status
    status = db.Column(db.Enum('sent', 'read', 'archived'), default='sent')
    
    # Dată
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Relații
    professor = db.relationship('User', foreign_keys=[professor_id], backref='feedbacks_given')
    student = db.relationship('User', foreign_keys=[student_id], backref='feedbacks_received')
    lesson = db.relationship('Lesson', backref='feedbacks')
    quiz_submission = db.relationship('QuizSubmission', backref='feedback')
    
    def __repr__(self):
        return f'<Feedback from professor {self.professor_id} to student {self.student_id}>'
    
    def mark_as_read(self):
        """Marchează feedback-ul ca citit"""
        self.status = 'read'
        self.read_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'professor_id': self.professor_id,
            'professor_name': self.professor.get_full_name(),
            'student_id': self.student_id,
            'student_name': self.student.get_full_name(),
            'lesson_id': self.lesson_id,
            'lesson_title': self.lesson.title if self.lesson else None,
            'title': self.title,
            'content': self.content,
            'rating': self.rating,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None
        }


class QuestionBank(db.Model):
    """Bankă de întrebări pentru profesori"""
    __tablename__ = 'question_banks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Profesor proprietar
    professor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Info
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    
    # Dată
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relații
    professor = db.relationship('User', backref='question_banks')
    questions = db.relationship('BankQuestion', backref='bank', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<QuestionBank {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'professor_id': self.professor_id,
            'question_count': len(self.questions),
            'created_at': self.created_at.isoformat()
        }


class BankQuestion(db.Model):
    """Întrebări în banca de întrebări"""
    __tablename__ = 'bank_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Bank
    bank_id = db.Column(db.Integer, db.ForeignKey('question_banks.id'), nullable=False)
    
    # Conținut
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum('multiple_choice', 'essay', 'true_false'), default='multiple_choice')
    
    # Pentru multiple choice
    options = db.Column(db.JSON, nullable=True)  # {"A": "Option A", "B": "Option B", ...}
    correct_answer = db.Column(db.String(50), nullable=True)
    
    # Dificultate
    difficulty = db.Column(db.Integer, default=1)  # 1-5
    
    # Dată
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BankQuestion {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'bank_id': self.bank_id,
            'text': self.text,
            'question_type': self.question_type,
            'options': self.options,
            'correct_answer': self.correct_answer,
            'difficulty': self.difficulty,
            'created_at': self.created_at.isoformat()
        }