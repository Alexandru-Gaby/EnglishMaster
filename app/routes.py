from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Meeting, Lesson, Quiz, Question, QuizSubmission, Badge, UserBadge, UserProgress, Reward, Class, ClassStudent, Feedback, QuestionBank, BankQuestion
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, desc
import re
import json
import random
import string

main = Blueprint('main', __name__)

# Validare email cu regex
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ==================== RUTE PENTRU PAGINI ====================

@main.route('/')
def index():
    """Pagina principală"""
    return render_template('home.html')

@main.route('/register')
def register_page():
    """Pagina de înregistrare"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('register.html')

@main.route('/login')
def login_page():
    """Pagina de autentificare"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@main.route('/dashboard')
@login_required
def dashboard():
    """Pagina principală după autentificare"""
    # Obține întâlnirile utilizatorului
    if current_user.role == 'professor':
        meetings = Meeting.query.filter_by(professor_id=current_user.id).order_by(Meeting.meeting_date.desc()).limit(5).all()
    else:
        meetings = Meeting.query.filter_by(student_id=current_user.id).order_by(Meeting.meeting_date.desc()).limit(5).all()
    
    return render_template('dashboard.html', user=current_user, meetings=meetings)

@main.route('/profile')
@login_required
def profile():
    """Pagina de profil a utilizatorului"""
    # Obține întâlnirile utilizatorului
    if current_user.role == 'professor':
        meetings = Meeting.query.filter_by(professor_id=current_user.id).order_by(Meeting.meeting_date.desc()).limit(5).all()
    else:
        meetings = Meeting.query.filter_by(student_id=current_user.id).order_by(Meeting.meeting_date.desc()).limit(5).all()
    
    return render_template('profile.html', user=current_user, meetings=meetings)

@main.route('/professors')
@login_required
def professors_page():
    """Pagina cu lista de profesori"""
    professors = User.query.filter_by(role='professor', is_available=True).all()
    return render_template('professors.html', professors=professors)

@main.route('/meetings')
@login_required
def meetings_page():
    """Pagina cu toate întâlnirile utilizatorului"""
    if current_user.role == 'professor':
        meetings = Meeting.query.filter_by(professor_id=current_user.id).order_by(Meeting.meeting_date.desc()).all()
    else:
        meetings = Meeting.query.filter_by(student_id=current_user.id).order_by(Meeting.meeting_date.desc()).all()
    
    return render_template('meetings.html', meetings=meetings)

@main.route('/lessons')
@login_required
def lessons_page():
    """Pagina cu toate lecțiile"""
    # Obține filtrul de nivel din query params
    level_filter = request.args.get('level', 'all')
    
    # Query de bază - doar lecții publicate
    query = Lesson.query.filter_by(status='published')
    
    # Aplică filtrul de nivel
    if level_filter != 'all':
        query = query.filter_by(level=level_filter)
    
    # Ordonează după dată (cele mai noi primele)
    lessons = query.order_by(Lesson.created_at.desc()).all()
    
    return render_template('lessons.html', lessons=lessons, current_level=level_filter)


@main.route('/my-lessons')
@login_required
def my_lessons():
    """Pagină pentru profesori: listează lecțiile create de profesor și permite crearea unora noi"""
    if current_user.role != 'professor':
        return redirect(url_for('main.dashboard'))

    lessons = Lesson.query.filter_by(professor_id=current_user.id).order_by(Lesson.created_at.desc()).all()
    return render_template('my_lessons.html', lessons=lessons)


@main.route('/lessons/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    """Pagina de detalii pentru o lecție"""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    # Incrementează nr de vizualizări
    lesson.increment_views()
    
    # Obține sau creează progresul utilizatorului pentru această lecție
    progress = UserProgress.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    if not progress:
        progress = UserProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            status='in_progress',
            started_at=datetime.utcnow()
        )
        db.session.add(progress)
        db.session.commit()
    else:
        # Actualizează ultima accesare
        progress.last_accessed = datetime.utcnow()
        if progress.status == 'not_started':
            progress.status = 'in_progress'
            progress.started_at = datetime.utcnow()
        db.session.commit()
    
    # Găsește quiz-ul pentru lecția curentă
    quiz = Quiz.query.filter_by(lesson_id=lesson_id).first()
    
    # Găsește încercările anterioare
    submissions = QuizSubmission.query.filter_by(
        user_id=current_user.id,
        lesson_id=lesson_id
    ).order_by(QuizSubmission.submitted_at.desc()).all()
    
    return render_template('lesson_detail.html', 
                         lesson=lesson, 
                         progress=progress,
                         quiz=quiz,
                         submissions=submissions)

@main.route('/quiz/<int:quiz_id>')
@login_required
def quiz_page(quiz_id):
    """Pagina pentru a lua un quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    lesson = quiz.lesson
    
    # Verifică numărul de încercări
    attempts = QuizSubmission.query.filter_by(
        user_id=current_user.id,
        quiz_id=quiz_id
    ).count()
    
    if attempts >= quiz.max_attempts:
        return redirect(url_for('main.lesson_detail', 
                              lesson_id=lesson.id,
                              error='max_attempts'))
    
    # Obține întrebările
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    
    return render_template('quiz.html', 
                         quiz=quiz, 
                         lesson=lesson,
                         questions=questions,
                         attempt_number=attempts + 1)

@main.route('/quiz/<int:quiz_id>/results/<int:submission_id>')
@login_required
def quiz_results(quiz_id, submission_id):
    """Pagina cu rezultatele quiz-ului"""
    submission = QuizSubmission.query.get_or_404(submission_id)
    
    # Verificăm că submission-ul aparține utilizatorului curent
    if submission.user_id != current_user.id:
        return redirect(url_for('main.dashboard'))
    
    quiz = submission.quiz
    lesson = submission.lesson
    
    # Obține întrebările și răspunsurile
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    user_answers = json.loads(submission.answers)
    
    # Găsește badge-urile câștigate (dacă există)
    new_badges = []
    if submission.passed:
        new_badges = check_and_award_badges(current_user)
        # Verifică și acordă recompense
        check_and_award_rewards(current_user)
    
    return render_template('quiz_results.html',
                         submission=submission,
                         quiz=quiz,
                         lesson=lesson,
                         questions=questions,
                         user_answers=user_answers,
                         new_badges=new_badges)

@main.route('/leaderboard')
@login_required
def leaderboard_page():
    """Pagina cu clasamentele"""
    return render_template('leaderboard.html')

@main.route('/rewards')
@login_required
def rewards_page():
    """Pagina cu recompensele utilizatorului"""
    rewards = Reward.query.filter_by(user_id=current_user.id)\
        .order_by(Reward.earned_at.desc()).all()
    
    return render_template('rewards.html', rewards=rewards)

@main.route('/class/<int:class_id>')
@login_required
def classroom_detail(class_id):
    """Pagina detalii clasă"""
    try:
        cls = Class.query.get(class_id)
        if not cls:
            return "Not Found - Clasă inexistentă!", 404
        
        # Verifică permisiuni
        is_professor = cls.professor_id == current_user.id
        is_student = any(cs.student_id == current_user.id for cs in cls.students)
        
        if not is_professor and not is_student:
            flash('Nu ai permisiunea să vizualizezi această clasă!', 'error')
            return redirect(url_for('main.professor_dashboard'))
        
        return render_template('classroom_detail.html', cls=cls, is_professor=is_professor)
    except Exception as e:
        print(f"Eroare: {str(e)}")
        return "Not Found", 404

@main.route('/join-class')
@login_required
def join_class_page():
    """Pagina pentru studenți să se alăture unei clase"""
    if current_user.role != 'user':
        flash('Această pagină este doar pentru studenți!', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('join_class.html')

@main.route('/my-classes')
@login_required
def my_classes():
    """Pagina cu clasele studenților - acces din navbar"""
    if current_user.role != 'user':
        return redirect(url_for('main.dashboard'))
    
    # Obține clasele în care studentul e înscris
    class_ids = [cs.class_id for cs in ClassStudent.query.filter_by(student_id=current_user.id).all()]
    classes = Class.query.filter(Class.id.in_(class_ids)).order_by(Class.created_at.desc()).all() if class_ids else []
    
    return render_template('my_classes.html', classes=classes)

@main.route('/professor-dashboard')
@login_required
def professor_dashboard():
    """Pagina panou profesor (clase, întrebări, feedback)"""
    if current_user.role != 'professor':
        return redirect(url_for('main.dashboard'))
    return render_template('professor_dashboard.html')


# Pagina detaliu Bancă Întrebări (HTML)
@main.route('/question-banks/<int:bank_id>')
@login_required
def question_bank_detail(bank_id):
    """Pagina detaliu pentru o bancă de întrebări (profesor proprietar)"""
    bank = QuestionBank.query.get_or_404(bank_id)
    # Permisiune: doar profesorul proprietar
    if current_user.role != 'professor' or bank.professor_id != current_user.id:
        return redirect(url_for('main.professor_dashboard'))

    questions = BankQuestion.query.filter_by(bank_id=bank_id).order_by(BankQuestion.created_at.desc()).all()
    return render_template('question_bank_detail.html', bank=bank, questions=questions)

@main.route('/logout')
@login_required
def logout():
    """Deconectare utilizator"""
    logout_user()
    return redirect(url_for('main.index'))

# ==================== API ENDPOINTS - AUTENTIFICARE ====================

@main.route('/api/register', methods=['POST'])
def api_register():
    """API Endpoint pentru înregistrare utilizator nou"""
    try:
        data = request.get_json()
        
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        role = data.get('role', 'user')  # user sau professor
        
        # Validare
        if not all([first_name, last_name, email, password]):
            return jsonify({'success': False, 'error': 'Toate câmpurile sunt obligatorii!'}), 400
        
        if len(first_name) < 2 or len(last_name) < 2:
            return jsonify({'success': False, 'error': 'Numele și prenumele trebuie să aibă cel puțin 2 caractere!'}), 400
        
        if not is_valid_email(email):
            return jsonify({'success': False, 'error': 'Adresa de email nu este validă!'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Parola trebuie să aibă cel puțin 6 caractere!'}), 400
        
        # Verifică dacă emailul există deja
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'error': 'Acest email este deja înregistrat!'}), 400
               
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role if role in ['user', 'professor'] else 'user'
        )
        new_user.set_password(password)
        
        # Dacă e profesor, adaugă info suplimentară
        if role == 'professor':
            new_user.bio = data.get('bio', 'Profesor de limba engleză')
            new_user.specialization = data.get('specialization', 'Gramatică și Vocabular')
            new_user.is_available = True
        
        new_user.points = 150
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cont creat cu succes! Te poți autentifica acum.',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la înregistrare: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare la înregistrare.'}), 500

@main.route('/api/login', methods=['POST'])
def api_login():
    """API Endpoint pentru autentificare utilizator"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email și parola sunt obligatorii!'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return jsonify({
                'success': True,
                'message': f'Bun venit, {user.first_name}!',
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'success': False, 'error': 'Email sau parolă incorectă!'}), 401
            
    except Exception as e:
        print(f"Eroare la autentificare: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare la autentificare.'}), 500

# ==================== API ENDPOINTS - PROFESORI ====================

@main.route('/api/professors', methods=['GET'])
@login_required
def api_get_professors():
    """Obține lista de profesori disponibili"""
    try:
        professors = User.query.filter_by(role='professor', is_available=True).all()
        
        return jsonify({
            'success': True,
            'professors': [prof.to_dict() for prof in professors]
        }), 200
        
    except Exception as e:
        print(f"Eroare la obținerea profesorilor: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

# ==================== API ENDPOINTS - MEETINGS ====================

@main.route('/api/meetings/create', methods=['POST'])
@login_required
def api_create_meeting():
    """Creează o întâlnire nouă (student -> profesor)"""
    try:
        data = request.get_json()
        
        professor_id = data.get('professor_id')
        meeting_date_str = data.get('meeting_date')  # Format: "2025-11-25T14:30"
        student_message = data.get('message', '').strip()
        
        # Validare
        if not professor_id or not meeting_date_str:
            return jsonify({'success': False, 'error': 'Profesorul și data sunt obligatorii!'}), 400
        
        # Verifică punctele utilizatorului
        if not current_user.can_request_feedback():
            return jsonify({
                'success': False, 
                'error': f'Nu ai suficiente puncte! Ai nevoie de 500 puncte. Ai doar {current_user.points} puncte.'
            }), 400
        
        # Verifică dacă profesorul există
        professor = User.query.get(professor_id)
        if not professor or professor.role != 'professor':
            return jsonify({'success': False, 'error': 'Profesor invalid!'}), 400
        
        if not professor.is_available:
            return jsonify({'success': False, 'error': 'Acest profesor nu este disponibil momentan.'}), 400
        
        # Parsează data
        try:
            meeting_date = datetime.fromisoformat(meeting_date_str)
        except ValueError:
            return jsonify({'success': False, 'error': 'Format de dată invalid!'}), 400
        
        # Verifică că data este în viitor
        if meeting_date <= datetime.now():
            return jsonify({'success': False, 'error': 'Data întâlnirii trebuie să fie în viitor!'}), 400
        
        # Creează întâlnirea
        new_meeting = Meeting(
            student_id=current_user.id,
            professor_id=professor_id,
            meeting_date=meeting_date,
            student_message=student_message,
            status='pending',
            points_cost=500
        )
        
        # Scade punctele
        current_user.deduct_points_for_feedback()
        
        db.session.add(new_meeting)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cerere de întâlnire trimisă! Profesorul va primi o notificare.',
            'meeting': new_meeting.to_dict(),
            'remaining_points': current_user.points
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la crearea întâlnirii: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare la programarea întâlnirii.'}), 500

@main.route('/api/meetings/<int:meeting_id>/respond', methods=['POST'])
@login_required
def api_respond_meeting(meeting_id):
    """Profesorul răspunde la o cerere de întâlnire"""
    try:
        meeting = Meeting.query.get(meeting_id)
        
        if not meeting:
            return jsonify({'success': False, 'error': 'Întâlnire inexistentă!'}), 404
        
        # Verifică că utilizatorul curent este profesorul pentru această întâlnire
        if meeting.professor_id != current_user.id:
            return jsonify({'success': False, 'error': 'Nu ai permisiunea să răspunzi la această cerere!'}), 403
        
        data = request.get_json()
        action = data.get('action')  # 'confirm' sau 'reject'
        response_message = data.get('message', '').strip()
        meeting_link = data.get('meeting_link', '').strip()
        
        if action == 'confirm':
            meeting.status = 'confirmed'
            meeting.professor_response = response_message or 'Întâlnire confirmată!'
            meeting.meeting_link = meeting_link
            message = 'Întâlnire confirmată cu succes!'
        elif action == 'reject':
            meeting.status = 'rejected'
            meeting.professor_response = response_message or 'Din păcate, nu pot confirma această întâlnire.'
            
            # Returnează punctele studentului
            student = User.query.get(meeting.student_id)
            student.points += meeting.points_cost
            
            message = 'Cerere respinsă. Punctele au fost returnate studentului.'
        else:
            return jsonify({'success': False, 'error': 'Acțiune invalidă!'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'meeting': meeting.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la răspunsul întâlnirii: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

@main.route('/api/meetings', methods=['GET'])
@login_required
def api_get_meetings():
    """Obține toate întâlnirile utilizatorului curent"""
    try:
        if current_user.role == 'professor':
            meetings = Meeting.query.filter_by(professor_id=current_user.id)\
                .order_by(Meeting.meeting_date.desc()).all()
        else:
            meetings = Meeting.query.filter_by(student_id=current_user.id)\
                .order_by(Meeting.meeting_date.desc()).all()
        
        return jsonify({
            'success': True,
            'meetings': [meeting.to_dict() for meeting in meetings]
        }), 200
        
    except Exception as e:
        print(f"Eroare la obținerea întâlnirilor: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

@main.route('/api/meetings/<int:meeting_id>/cancel', methods=['POST'])
@login_required
def api_cancel_meeting(meeting_id):
    """Anulează o întâlnire"""
    try:
        meeting = Meeting.query.get(meeting_id)
        
        if not meeting:
            return jsonify({'success': False, 'error': 'Întâlnire inexistentă!'}), 404
        
        # Verifică permisiuni
        if meeting.student_id != current_user.id and meeting.professor_id != current_user.id:
            return jsonify({'success': False, 'error': 'Nu ai permisiunea să anulezi această întâlnire!'}), 403
        
        if not meeting.can_cancel():
            return jsonify({'success': False, 'error': 'Această întâlnire nu poate fi anulată!'}), 400
        
        # păstrează statusul anterior pentru a decide dacă returnăm punctele
        previous_status = meeting.status
        meeting.status = 'cancelled'
        
        # Returnează punctele dacă e anulată de student sau profesor
        if meeting.status == 'pending' or meeting.status == 'confirmed':
            student = User.query.get(meeting.student_id)
            student.points += meeting.points_cost
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Întâlnire anulată cu succes! Punctele au fost returnate.',
            'meeting': meeting.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la anularea întâlnirii: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

@main.route('/api/user/current', methods=['GET'])
@login_required
def api_current_user():
    """Returnează informații despre utilizatorul curent"""
    return jsonify({'success': True, 'user': current_user.to_dict()}), 200

# ==================== API ENDPOINTS - LECȚII ====================

@main.route('/api/lessons', methods=['GET'])
@login_required
def api_get_lessons():
    """Obține lista de lecții cu opțiune de filtrare"""
    try:
        level = request.args.get('level', 'all')
        category = request.args.get('category', 'all')
        
        # Query de bază
        query = Lesson.query.filter_by(status='published')
        
        # Filtrare după nivel
        if level != 'all':
            query = query.filter_by(level=level)
        
        # Filtrare după categorie
        if category != 'all':
            query = query.filter_by(category=category)
        
        # Ordonare
        lessons = query.order_by(Lesson.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'lessons': [lesson.to_dict() for lesson in lessons],
            'count': len(lessons)
        }), 200
        
    except Exception as e:
        print(f"Eroare la obținerea lecțiilor: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

@main.route('/api/lessons/<int:lesson_id>', methods=['GET'])
@login_required
def api_get_lesson(lesson_id):
    """Obține detaliile unei lecții"""
    try:
        lesson = Lesson.query.get(lesson_id)
        
        if not lesson:
            return jsonify({'success': False, 'error': 'Lecție inexistentă!'}), 404
        
        if lesson.status != 'published':
            return jsonify({'success': False, 'error': 'Această lecție nu este disponibilă.'}), 403
        
        return jsonify({
            'success': True,
            'lesson': lesson.to_dict()
        }), 200
        
    except Exception as e:
        print(f"Eroare la obținerea lecției: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

@main.route('/api/lessons/create', methods=['POST'])
@login_required
def api_create_lesson():
    """Creează o lecție nouă (doar pentru profesori)"""
    try:
        # Verifică că utilizatorul este profesor
        if current_user.role != 'professor':
            return jsonify({'success': False, 'error': 'Doar profesorii pot crea lecții!'}), 403
        
        data = request.get_json()
        
        # Validare
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        content = data.get('content', '').strip()
        level = data.get('level', 'beginner')
        category = data.get('category', '').strip()
        duration_minutes = data.get('duration_minutes', 30)
        difficulty = data.get('difficulty', 3)
        
        if not all([title, description, content]):
            return jsonify({'success': False, 'error': 'Titlu, descriere și conținut sunt obligatorii!'}), 400
        
        if level not in ['beginner', 'intermediate', 'advanced']:
            return jsonify({'success': False, 'error': 'Nivel invalid!'}), 400
        
        # Creează lecția
        new_lesson = Lesson(
            title=title,
            description=description,
            content=content,
            level=level,
            category=category if category else None,
            professor_id=current_user.id,
            duration_minutes=duration_minutes,
            difficulty=difficulty,
            status='published'
        )
        
        db.session.add(new_lesson)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Lecție creată cu succes!',
            'lesson': new_lesson.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la crearea lecției: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare la crearea lecției.'}), 500

# ==================== API ENDPOINTS - QUIZ ====================

@main.route('/api/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def api_submit_quiz(quiz_id):
    """Trimite răspunsurile la quiz și calculează scorul"""
    try:
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return jsonify({'success': False, 'error': 'Quiz inexistent!'}), 404
        
        # Verifică numărul de încercări
        attempts = QuizSubmission.query.filter_by(
            user_id=current_user.id,
            quiz_id=quiz_id
        ).count()
        
        if attempts >= quiz.max_attempts:
            return jsonify({'success': False, 'error': 'Ai atins numărul maxim de încercări!'}), 400
        
        data = request.get_json()
        answers = data.get('answers', {})  # Format: {"1": "A", "2": "B", ...}
        time_taken = data.get('time_taken_seconds', 0)
        
        # Obține întrebările
        questions = Question.query.filter_by(quiz_id=quiz_id).all()
        
        # Calculează scorul
        total_points = sum(q.points for q in questions)
        earned_points = 0
        
        for question in questions:
            user_answer = answers.get(str(question.id))
            if user_answer and user_answer.upper() == question.correct_answer.upper():
                earned_points += question.points
        
        # Scor procentual
        score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        passed = score_percentage >= quiz.passing_score
        
        # Puncte recompensă
        points_reward = quiz.points_reward if passed else int(quiz.points_reward * 0.3)
        
        # Creează submission
        submission = QuizSubmission(
            user_id=current_user.id,
            quiz_id=quiz_id,
            lesson_id=quiz.lesson_id,
            answers=json.dumps(answers),
            score=round(score_percentage, 2),
            points_earned=points_reward,
            passed=passed,
            time_taken_seconds=time_taken,
            attempt_number=attempts + 1
        )
        
        db.session.add(submission)
        
        # Adaugă puncte utilizatorului
        current_user.points += points_reward
        
        # Actualizează progresul
        progress = UserProgress.query.filter_by(
            user_id=current_user.id,
            lesson_id=quiz.lesson_id
        ).first()
        
        if progress:
            progress.quiz_attempts += 1
            progress.best_score = max(progress.best_score, score_percentage)
            
            if passed and progress.status != 'completed':
                progress.status = 'completed'
                progress.completed_at = datetime.utcnow()
                progress.progress_percentage = 100
                
                # Incrementează completions la lecție
                lesson = Lesson.query.get(quiz.lesson_id)
                if lesson:
                    lesson.completions += 1
        
        db.session.commit()
        
        # Verifică badge-uri
        new_badges = check_and_award_badges(current_user)
        
        return jsonify({
            'success': True,
            'submission_id': submission.id,
            'score': score_percentage,
            'points_earned': points_reward,
            'passed': passed,
            'total_points': current_user.points,
            'new_badges': [b.to_dict() for b in new_badges],
            'message': 'Felicitări! Ai promovat!' if passed else 'Mai încearcă o dată!'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la submit quiz: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare la evaluarea quiz-ului.'}), 500

@main.route('/api/progress', methods=['GET'])
@login_required
def api_get_progress():
    """Obține progresul utilizatorului"""
    try:
        progress_list = UserProgress.query.filter_by(user_id=current_user.id).all()
        
        # Statistici generale
        total_lessons = Lesson.query.filter_by(status='published').count()
        completed_lessons = len([p for p in progress_list if p.status == 'completed'])
        in_progress_lessons = len([p for p in progress_list if p.status == 'in_progress'])
        
        # Badge-uri
        user_badges = UserBadge.query.filter_by(user_id=current_user.id).all()
        badges = [ub.badge.to_dict() for ub in user_badges]
        
        # Submission-uri recente
        recent_submissions = QuizSubmission.query.filter_by(user_id=current_user.id)\
            .order_by(QuizSubmission.submitted_at.desc())\
            .limit(5).all()

        # Streak (zile consecutive) — considerăm doar quiz-urile promovate ca activitate
        passed_subs = QuizSubmission.query.filter_by(user_id=current_user.id, passed=True)\
            .order_by(QuizSubmission.submitted_at.desc()).all()

        passed_dates = set()
        for s in passed_subs:
            dt = s.submitted_at
            if not dt:
                continue
            # normalize to UTC date when tz-aware
            try:
                if dt.tzinfo is not None:
                    d = dt.astimezone(timezone.utc).date()
                else:
                    d = dt.date()
            except Exception:
                d = dt.date()
            passed_dates.add(d)

        # count consecutive days ending today (UTC)
        consecutive_days = 0
        today = datetime.now(timezone.utc).date()
        cur = today
        while cur in passed_dates:
            consecutive_days += 1
            cur = cur - timedelta(days=1)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_points': current_user.points,
                'total_lessons': total_lessons,
                'completed_lessons': completed_lessons,
                'in_progress_lessons': in_progress_lessons,
                'completion_rate': round((completed_lessons / total_lessons * 100), 1) if total_lessons > 0 else 0,
                'total_badges': len(badges),
                'consecutive_days': consecutive_days
            },
            'progress': [p.to_dict() for p in progress_list],
            'badges': badges,
            'recent_quizzes': [
                {
                    'id': s.id,
                    'quiz_id': s.quiz_id,
                    'lesson_id': s.lesson_id,
                    'lesson_title': s.lesson.title if s.lesson else None,
                    'score': s.score,
                    'passed': s.passed,
                    'submitted_at': s.submitted_at.isoformat()
                } for s in recent_submissions
            ]
        }), 200
        
    except Exception as e:
        print(f"Eroare la obținerea progresului: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

# Funcție helper pentru verificare și acordare badge-uri
def check_and_award_badges(user):
    """Verifică și acordă badge-uri utilizatorului"""
    new_badges = []
    
    # Obține toate badge-urile
    all_badges = Badge.query.all()
    
    # Obține badge-urile deja câștigate
    earned_badge_ids = [ub.badge_id for ub in UserBadge.query.filter_by(user_id=user.id).all()]
    
    for badge in all_badges:
        # Dacă utilizatorul deja are acest badge, skip
        if badge.id in earned_badge_ids:
            continue
        
        # Verifică criteriile
        earned = False
        
        if badge.criteria_type == 'points':
            earned = user.points >= badge.criteria_value
        
        elif badge.criteria_type == 'lessons_completed':
            completed = UserProgress.query.filter_by(
                user_id=user.id,
                status='completed'
            ).count()
            earned = completed >= badge.criteria_value
        
        elif badge.criteria_type == 'perfect_score':
            perfect_scores = QuizSubmission.query.filter_by(
                user_id=user.id,
                score=100.0
            ).count()
            earned = perfect_scores >= badge.criteria_value
        
        # Acordă badge-ul
        if earned:
            user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
            db.session.add(user_badge)
            new_badges.append(badge)
    
    if new_badges:
        db.session.commit()
    
    return new_badges

# ==================== API ENDPOINTS - CLASAMENTE ====================

@main.route('/api/leaderboard/global', methods=['GET'])
@login_required
def api_global_leaderboard():
    """Clasament global utilizatori după puncte"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        
        # Query pentru utilizatori (exclude admin și profesori dacă vrei)
        query = User.query.filter_by(role='user')\
            .order_by(User.points.desc())
        
        # Paginare
        total = query.count()
        users = query.limit(per_page).offset((page - 1) * per_page).all()
        
        # Găsește poziția utilizatorului curent
        current_user_rank = None
        if current_user.role == 'user':
            users_above = User.query.filter(
                User.role == 'user',
                User.points > current_user.points
            ).count()
            current_user_rank = users_above + 1
        
        leaderboard = []
        for idx, user in enumerate(users, start=(page - 1) * per_page + 1):
            # Calculează lecții completate
            completed_lessons = UserProgress.query.filter_by(
                user_id=user.id,
                status='completed'
            ).count()
            
            leaderboard.append({
                'rank': idx,
                'user_id': user.id,
                'name': user.get_full_name(),
                'points': user.points,
                'lessons_completed': completed_lessons,
                'is_current_user': user.id == current_user.id
            })
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'current_user_rank': current_user_rank,
            'total_users': total,
            'page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        print(f"Eroare la obținerea clasamentului: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

@main.route('/api/leaderboard/professors', methods=['GET'])
@login_required
def api_professors_leaderboard():
    """Clasament profesori după rating și lecții create"""
    try:
        level = request.args.get('level', 'all')  # all, beginner, intermediate, advanced
        
        # Query de bază
        query = User.query.filter_by(role='professor', is_available=True)
        
        # Calculează scorul pentru fiecare profesor
        professors_data = []
        for professor in query.all():
            # Filtrează lecții după nivel dacă e necesar
            lessons_query = Lesson.query.filter_by(professor_id=professor.id, status='published')
            if level != 'all':
                lessons_query = lessons_query.filter_by(level=level)
            
            lessons = lessons_query.all()
            total_lessons = len(lessons)
            
            # Calculează rating mediu din lecții
            total_rating = sum(l.rating for l in lessons)
            avg_rating = (total_rating / total_lessons) if total_lessons > 0 else 0
            
            # Calculează views totale
            total_views = sum(l.views for l in lessons)
            
            # Scor compus: rating * 100 + lecții * 10 + views
            score = (avg_rating * 100) + (total_lessons * 10) + (total_views * 0.1)
            
            professors_data.append({
                'professor_id': professor.id,
                'name': professor.get_full_name(),
                'specialization': professor.specialization,
                'rating': round(professor.rating, 2),
                'total_reviews': professor.total_reviews,
                'total_lessons': total_lessons,
                'total_views': total_views,
                'avg_lesson_rating': round(avg_rating, 2),
                'score': round(score, 2)
            })
        
        # Sortează după scor
        professors_data.sort(key=lambda x: x['score'], reverse=True)
        
        # Adaugă rang
        for idx, prof in enumerate(professors_data, start=1):
            prof['rank'] = idx
        
        return jsonify({
            'success': True,
            'leaderboard': professors_data,
            'level': level,
            'total_professors': len(professors_data)
        }), 200
        
    except Exception as e:
        print(f"Eroare la clasamentul profesorilor: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

# ==================== API ENDPOINTS - RECOMPENSE ====================

@main.route('/api/rewards', methods=['GET'])
@login_required
def api_get_rewards():
    """Obține toate recompensele utilizatorului"""
    try:
        rewards = Reward.query.filter_by(user_id=current_user.id)\
            .order_by(Reward.earned_at.desc()).all()
        
        return jsonify({
            'success': True,
            'rewards': [r.to_dict() for r in rewards],
            'total': len(rewards),
            'pending': len([r for r in rewards if r.status == 'pending' and not r.is_expired()])
        }), 200
        
    except Exception as e:
        print(f"Eroare la obținerea recompenselor: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


@main.route('/api/rewards/generate', methods=['POST'])
@login_required
def api_generate_rewards():
    """Generează recompense pentru toți utilizatorii (admin only).
    Poate fi folosit ca job periodic sau endpoint manual pentru testare."""
    try:
        if current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Doar adminii pot genera recompense.'}), 403

        users = User.query.filter_by(role='user').all()
        total_new = 0
        details = []
        for u in users:
            before = len(Reward.query.filter_by(user_id=u.id).all())
            new = check_and_award_rewards(u)
            after = len(Reward.query.filter_by(user_id=u.id).all())
            created = after - before
            total_new += created
            if created > 0:
                details.append({'user_id': u.id, 'created': created})

        return jsonify({'success': True, 'message': 'Generare recompense finalizată.', 'total_created': total_new, 'details': details}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Eroare la generarea recompenselor: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare la generarea recompenselor.'}), 500

@main.route('/api/rewards/<int:reward_id>/claim', methods=['POST'])
@login_required
def api_claim_reward(reward_id):
    """Revendică o recompensă"""
    try:
        reward = Reward.query.get(reward_id)
        
        if not reward:
            return jsonify({'success': False, 'error': 'Recompensă inexistentă!'}), 404
        
        if reward.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Nu ai permisiunea!'}), 403
        
        if reward.status != 'pending':
            return jsonify({'success': False, 'error': 'Recompensa a fost deja revendicată sau a expirat!'}), 400
        
        if reward.is_expired():
            reward.status = 'expired'
            db.session.commit()
            return jsonify({'success': False, 'error': 'Recompensa a expirat!'}), 400
        
        # Revendică recompensa
        if reward.claim():
            # Aplică recompensa
            if reward.reward_type == 'bonus_points':
                current_user.points += reward.value
            elif reward.reward_type == 'premium_trial':
                current_user.premium = True
                # TODO: Setează data expirării trial-ului
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Recompensă revendicată cu succes!',
                'reward': reward.to_dict(),
                'new_points': current_user.points
            }), 200
        else:
            return jsonify({'success': False, 'error': 'Nu s-a putut revendica recompensa!'}), 400
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la revendicare: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

# Funcție helper pentru verificare și acordare recompense
def check_and_award_rewards(user):
    """Verifică și acordă recompense bazate pe puncte"""
    new_rewards = []
    
    # Recompense pentru anumite praguri de puncte
    reward_tiers = [
        {'points': 200, 'bonus': 50, 'description': 'Bonus pentru 200 puncte!'},
        {'points': 500, 'bonus': 100, 'description': 'Bonus pentru 500 puncte!'},
        {'points': 1000, 'bonus': 200, 'description': 'Bonus pentru 1000 puncte!'},
        {'points': 2000, 'bonus': 500, 'description': 'Bonus masiv pentru 2000 puncte!'}
    ]
    
    for tier in reward_tiers:
        # Verifică dacă utilizatorul a atins pragul
        if user.points >= tier['points']:
            # Verifică dacă nu a primit deja această recompensă
            existing = Reward.query.filter_by(
                user_id=user.id,
                reward_type='bonus_points',
                value=tier['bonus']
            ).first()
            
            if not existing:
                reward = Reward(
                    user_id=user.id,
                    reward_type='bonus_points',
                    value=tier['bonus'],
                    description=tier['description'],
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                db.session.add(reward)
                new_rewards.append(reward)
    
    # Recompensă pentru 5 lecții completate
    completed_count = UserProgress.query.filter_by(
        user_id=user.id,
        status='completed'
    ).count()
    
    if completed_count >= 5:
        existing = Reward.query.filter_by(
            user_id=user.id,
            reward_type='free_feedback',
            description='Feedback gratuit pentru 5 lecții completate!'
        ).first()
        
        if not existing:
            reward = Reward(
                user_id=user.id,
                reward_type='free_feedback',
                value=1,
                description='Feedback gratuit pentru 5 lecții completate!',
                expires_at=datetime.utcnow() + timedelta(days=60)
            )
            db.session.add(reward)
            new_rewards.append(reward)
    
    if new_rewards:
        db.session.commit()
    
    return new_rewards


# ==================== API ENDPOINTS - SPRINT 5: CLASE ====================

@main.route('/api/classes/create', methods=['POST'])
@login_required
def api_create_class():
    """Profesor creează o clasă nouă (US013)"""
    try:
        if current_user.role != 'professor':
            return jsonify({'success': False, 'error': 'Doar profesorii pot crea clase!'}), 403
        
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Numele clasei este obligatoriu!'}), 400
        
        # Generează cod unic pentru clasă
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        new_class = Class(
            professor_id=current_user.id,
            name=name,
            description=description,
            code=code,
            status='active'
        )
        
        db.session.add(new_class)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Clasă creată cu succes!',
            'class': new_class.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la crearea clasei: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


@main.route('/api/classes/<int:class_id>/add-student', methods=['POST'])
@login_required
def api_add_student_to_class(class_id):
    """Profesor adaugă student la clasă (US014)"""
    try:
        cls = Class.query.get(class_id)
        if not cls:
            return jsonify({'success': False, 'error': 'Clasă inexistentă!'}), 404
        
        if cls.professor_id != current_user.id:
            return jsonify({'success': False, 'error': 'Nu ai permisiunea!'}), 403
        
        data = request.get_json()
        student_email = data.get('student_email', '').strip().lower()
        
        if not student_email:
            return jsonify({'success': False, 'error': 'Email student obligatoriu!'}), 400
        
        student = User.query.filter_by(email=student_email).first()
        if not student or student.role != 'user':
            return jsonify({'success': False, 'error': 'Student nu găsit!'}), 404
        
        # Verifică dacă e deja în clasă
        existing = ClassStudent.query.filter_by(class_id=class_id, student_id=student.id).first()
        if existing:
            return jsonify({'success': False, 'error': 'Student deja în clasă!'}), 400
        
        class_student = ClassStudent(class_id=class_id, student_id=student.id)
        db.session.add(class_student)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{student.get_full_name()} adăugat la clasă!',
            'student': class_student.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la adăugare student: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


@main.route('/api/classes/<int:class_id>/join', methods=['POST'])
@login_required
def api_join_class(class_id):
    """Student se alătură unei clase folosind cod (US014)"""
    try:
        cls = Class.query.get(class_id)
        if not cls:
            return jsonify({'success': False, 'error': 'Clasă inexistentă!'}), 404
        
        if current_user.role != 'user':
            return jsonify({'success': False, 'error': 'Doar studenții pot se alătura claselor!'}), 403
        
        data = request.get_json()
        code = data.get('code', '').strip()
        
        if code != cls.code:
            return jsonify({'success': False, 'error': 'Cod invalid!'}), 400
        
        existing = ClassStudent.query.filter_by(class_id=class_id, student_id=current_user.id).first()
        if existing:
            return jsonify({'success': False, 'error': 'Ești deja în această clasă!'}), 400
        
        class_student = ClassStudent(class_id=class_id, student_id=current_user.id)
        db.session.add(class_student)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Te-ai alăturat clasei {cls.name}!',
            'class': cls.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la aderare clasă: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


@main.route('/api/classes', methods=['GET'])
@login_required
def api_get_classes():
    """Obține clasele - profesor"""
    try:
        # Verifică dacă caută o clasă specific după cod (pentru join)
        search_code = request.args.get('code', '').strip().upper()
        
        if search_code:
            # Caută clasa după cod (oricine poate căuta)
            cls = Class.query.filter(Class.code.ilike(search_code)).first()
            if cls:
                return jsonify({
                    'success': True,
                    'class': cls.to_dict()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Nu s-a găsit clasă cu acest cod!'
                }), 404
        
        # Fără parametru search - returnează clasele utilizatorului
        if current_user.role == 'professor':
            classes = Class.query.filter_by(professor_id=current_user.id).all()
        else:
            # Student - clasele în care e înscris
            class_ids = [cs.class_id for cs in ClassStudent.query.filter_by(student_id=current_user.id).all()]
            classes = Class.query.filter(Class.id.in_(class_ids)).all() if class_ids else []
        
        return jsonify({
            'success': True,
            'classes': [c.to_dict() for c in classes]
        }), 200
        
    except Exception as e:
        print(f"Eroare la obținerea claselor: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


@main.route('/api/classes/<int:class_id>', methods=['GET'])
@login_required
def api_get_class_detail(class_id):
    """Obține detaliile unei clase cu studenți (US015)"""
    try:
        cls = Class.query.get(class_id)
        if not cls:
            return jsonify({'success': False, 'error': 'Clasă inexistentă!'}), 404
        
        # Verifică permisiuni
        is_professor = cls.professor_id == current_user.id
        is_student = any(cs.student_id == current_user.id for cs in cls.students)
        
        if not is_professor and not is_student:
            return jsonify({'success': False, 'error': 'Nu ai permisiunea!'}), 403
        
        students = [cs.to_dict() for cs in cls.students]
        
        return jsonify({
            'success': True,
            'class': cls.to_dict(),
            'students': students,
            'is_professor': is_professor
        }), 200
        
    except Exception as e:
        print(f"Eroare la detalii clasă: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500

@main.route('/api/classes/<int:class_id>/feedback', methods=['GET'])
@login_required
def api_get_class_feedback(class_id):
    """Obține feedback-uri din clasă"""
    try:
        cls = Class.query.get(class_id)
        if not cls:
            return jsonify({'success': False, 'error': 'Clasă inexistentă!'}), 404
        
        # Verifică permisiuni
        is_professor = cls.professor_id == current_user.id
        is_student = any(cs.student_id == current_user.id for cs in cls.students)
        
        if not is_professor and not is_student:
            return jsonify({'success': False, 'error': 'Nu ai permisiunea!'}), 403
        
        # Obține studenții din clasă
        student_ids = [cs.student_id for cs in cls.students]
        
        # Feedback-uri trimise de profesor către studenții din această clasă
        feedbacks = Feedback.query.filter(
            Feedback.professor_id == cls.professor_id,
            Feedback.student_id.in_(student_ids)
        ).order_by(Feedback.created_at.desc()).all()
        
        result = []
        for f in feedbacks:
            result.append({
                'id': f.id,
                'student_name': f.student.get_full_name(),
                'professor_name': f.professor.get_full_name(),
                'title': f.title,
                'content': f.content,
                'message': f.content,  # Pentru compatibilitate cu frontend-ul vechi
                'rating': f.rating,
                'status': f.status,
                'created_at': f.created_at.isoformat(),
                'is_read': f.status == 'read'  # status e 'sent' sau 'read'
            })
        
        return jsonify({
            'success': True,
            'feedbacks': result
        }), 200
        
    except Exception as e:
        print(f"Eroare: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500



# ==================== API ENDPOINTS - SPRINT 5: ÎNTREBĂRI ====================

@main.route('/api/question-banks/create', methods=['POST'])
@login_required
def api_create_question_bank():
    """Profesor creează o bancă de întrebări (US013)"""
    try:
        if current_user.role != 'professor':
            return jsonify({'success': False, 'error': 'Doar profesorii pot crea bănci!'}), 403
        
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        category = data.get('category', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Numele băncii este obligatoriu!'}), 400
        
        bank = QuestionBank(
            professor_id=current_user.id,
            name=name,
            description=description,
            category=category
        )
        
        db.session.add(bank)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Bancă de întrebări creată!',
            'bank': bank.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la creare bancă: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


@main.route('/api/question-banks/<int:bank_id>/add-question', methods=['POST'])
@login_required
def api_add_question_to_bank(bank_id):
    """Profesor adaugă întrebare la bancă (US013)"""
    try:
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return jsonify({'success': False, 'error': 'Bancă inexistentă!'}), 404
        
        if bank.professor_id != current_user.id:
            return jsonify({'success': False, 'error': 'Nu ai permisiunea!'}), 403
        
        data = request.get_json()
        text = data.get('text', '').strip()
        question_type = data.get('question_type', 'multiple_choice')
        difficulty = data.get('difficulty', 1)
        
        if not text:
            return jsonify({'success': False, 'error': 'Text obligatoriu!'}), 400
        
        question = BankQuestion(
            bank_id=bank_id,
            text=text,
            question_type=question_type,
            options=data.get('options'),
            correct_answer=data.get('correct_answer'),
            difficulty=difficulty
        )
        
        db.session.add(question)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Întrebare adăugată!',
            'question': question.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la adăugare întrebare: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


@main.route('/api/question-banks', methods=['GET'])
@login_required
def api_get_question_banks():
    """Obține întrebări scrise de profesor (US013)"""
    try:
        if current_user.role != 'professor':
            return jsonify({'success': False, 'error': 'Numai profesori!'}), 403
        
        banks = QuestionBank.query.filter_by(professor_id=current_user.id).all()
        
        return jsonify({
            'success': True,
            'banks': [b.to_dict() for b in banks]
        }), 200
        
    except Exception as e:
        print(f"Eroare: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


# ==================== API ENDPOINTS - SPRINT 5: FEEDBACK ====================

@main.route('/api/feedback/send', methods=['POST'])
@login_required
def api_send_feedback():
    """Profesor trimite feedback personalizat (US017)"""
    try:
        if current_user.role != 'professor':
            return jsonify({'success': False, 'error': 'Doar profesorii pot trimite feedback!'}), 403
        
        data = request.get_json()
        student_id = data.get('student_id')
        # Acceptă atât 'message' cât și 'content' și 'title'
        message = data.get('message', '').strip()
        title = data.get('title', message[:50] if message else '').strip()  # Titlu auto din primele 50 caractere
        content = data.get('content', message).strip()  # Dacă nu e content, folosește message
        feedback_type = data.get('type', 'general')  # lesson, quiz, general
        lesson_id = data.get('lesson_id')
        rating = data.get('rating')
        
        if not all([student_id, message or content]):
            return jsonify({'success': False, 'error': 'Câmpuri obligatorii!'}), 400
        
        student = User.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': 'Student nu găsit!'}), 404
        
        # Dacă nu e titlu explicit, crează din mesaj
        if not title:
            title = f"Feedback - {feedback_type}"
        
        feedback = Feedback(
            professor_id=current_user.id,
            student_id=student_id,
            lesson_id=lesson_id,
            title=title,
            content=content or message,
            rating=int(rating) if rating else None,
            status='sent'
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Feedback trimis cu succes!',
            'feedback': feedback.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare feedback: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500
        db.session.rollback()
        print(f"Eroare feedback: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


@main.route('/api/feedback', methods=['GET'])
@login_required
def api_get_feedback():
    """Obține feedback-uri - student: primit, profesor: trimis"""
    try:
        if current_user.role == 'professor':
            feedbacks = Feedback.query.filter_by(professor_id=current_user.id)\
                .order_by(Feedback.created_at.desc()).all()
        else:
            feedbacks = Feedback.query.filter_by(student_id=current_user.id)\
                .order_by(Feedback.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'feedbacks': [f.to_dict() for f in feedbacks]
        }), 200
        
    except Exception as e:
        print(f"Eroare: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500


@main.route('/api/feedback/<int:feedback_id>/mark-read', methods=['POST'])
@login_required
def api_mark_feedback_read(feedback_id):
    """Student marchează feedback ca citit (US018)"""
    try:
        feedback = Feedback.query.get(feedback_id)
        if not feedback:
            return jsonify({'success': False, 'error': 'Feedback nu găsit!'}), 404
        
        if feedback.student_id != current_user.id:
            return jsonify({'success': False, 'error': 'Nu ai permisiunea!'}), 403
        
        feedback.mark_as_read()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Marcat ca citit!',
            'feedback': feedback.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Eroare: {str(e)}")
        return jsonify({'success': False, 'error': 'A apărut o eroare.'}), 500
    
    return new_rewards