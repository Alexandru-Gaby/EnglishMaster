from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Meeting, Lesson, Quiz, Question, QuizSubmission, Badge, UserBadge, UserProgress
from datetime import datetime
import re
import json

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
    return render_template('profile.html', user=current_user)

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
    
    return render_template('quiz_results.html',
                         submission=submission,
                         quiz=quiz,
                         lesson=lesson,
                         questions=questions,
                         user_answers=user_answers,
                         new_badges=new_badges)

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

        remaining_points = None
        # Returnează punctele doar dacă întâlnirea era pending sau confirmed
        if previous_status in ['pending', 'confirmed']:
            student = User.query.get(meeting.student_id)
            if student:
                student.points += meeting.points_cost
                remaining_points = student.points

        db.session.commit()

        message = 'Întâlnire anulată cu succes.'
        if remaining_points is not None:
            message += ' Punctele au fost returnate.'

        return jsonify({
            'success': True,
            'message': message,
            'meeting': meeting.to_dict(),
            'remaining_points': remaining_points
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
        
        return jsonify({
            'success': True,
            'stats': {
                'total_points': current_user.points,
                'total_lessons': total_lessons,
                'completed_lessons': completed_lessons,
                'in_progress_lessons': in_progress_lessons,
                'completion_rate': round((completed_lessons / total_lessons * 100), 1) if total_lessons > 0 else 0,
                'total_badges': len(badges)
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