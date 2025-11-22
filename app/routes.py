from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Meeting
from datetime import datetime
import re

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
        
        # Verificăm dacă emailul există deja
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'error': 'Acest email este deja înregistrat!'}), 400
        
        # Creeaza utilizatorul nou
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
        
        # Pentru DEMO: Oferim 150 puncte automat la înregistrare
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
                'error': f'Nu ai suficiente puncte! Ai nevoie de 100 puncte. Ai doar {current_user.points} puncte.'
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
            points_cost=100
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