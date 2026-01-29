# 📚 EnglishMaster - Sprint 1
Aplicație web educațională pentru învățarea limbii engleze prin gamification.

## 🎯 Sprint 1 - Autentificare
### Funcționalități Implementate

✅ Înregistrare utilizatori (US001)\
✅ Autentificare utilizatori (US002)\
✅ Bază de date MySQL configurată\
✅ Backend Flask complet funcțional\
✅ Frontend responsive (HTML/CSS/JS)\
✅ Validare client-side și server-side

## Pagina Home
![Pagina Home](Imagini/Pagina%20Home.png)

## Pagina Register
![Pagina Register](Imagini/Pagina%20Register.png)

## Pagina Login
![Pagina Login](Imagini/Pagina%20Login.png)

## Pagina Dashboard
![Pagina Dashboard](Imagini/Pagina%20Dashboard.png)

### 🛠️ Tehnologii Folosite

Backend: Python 3.10+ cu Flask,
Bază de Date: MySQL 8.0,
Frontend: HTML5, Jinja2, CSS3, JavaScript.
Autentificare: Flask-Login + Bcrypt,
ORM: SQLAlchemy

### 📦 Instalare și Rulare
1. Clonează repository-ul
git clone [URL_REPOSITORY]
cd englishmaster
2. Creează virtual environment
python -m venv venv

### Windows
```venv\Scripts\activate```

### Mac/Linux
``` source venv/bin/activate ```

3. Instalează dependențele
```pip install -r requirements.txt```
4. Configurează MySQL\
Intră în MySQL
```mysql -u root -p```

###  Creează baza de date
``` CREATE DATABASE englishmaster CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;```

### Creează utilizator (opțional)
``` CREATE USER 'englishmaster_user'@'localhost' IDENTIFIED BY 'parola_sigura'; 
GRANT ALL PRIVILEGES ON englishmaster.* TO 'englishmaster_user'@'localhost';
FLUSH PRIVILEGES;
EXIT; 
```
5. Configurează conexiunea\
Editează app/config.py și schimbă parola MySQL:
```pythonSQLALCHEMY_DATABASE_URL = 'mysql+pymysql://englishmaster_user:parola_user@localhost/englishmaster'```
6. Rulează aplicația\
```python run.py```

Aplicația va fi disponibilă la: http://localhost:5000\
📱 Pagini Disponibile

/ - Homepage\
/register - Înregistrare cont nou\
/login - Autentificare\
/dashboard - Dashboard utilizator (după autentificare)

Înregistrare cu succes → redirecționare la /login


### 📊 Structura Bazei de Date
### Tabelul users

| Câmp         | Tip             | Descriere                                       |
|--------------|-----------------|-------------------------------------------------|
| `id`         | `INT`           | **Primary Key**, Auto Increment (ID unic)       |
| `first_name` | `VARCHAR(100)`   | Prenume utilizator                              |
| `last_name`  | `VARCHAR(100)`   | Nume utilizator                                 |
| `email`      | `VARCHAR(255)`   | Email (UNIQUE)                                  |
| `password`   | `VARCHAR(255)`   | Parolă criptată (bcrypt)                       |
| `role`       | `ENUM`           | Rol (user/professor/admin)                      |
| `points`     | `INT`            | Puncte acumulate (default 0)                    |
| `premium`    | `BOOLEAN`        | Abonament premium (default FALSE)               |
| `created_at` | `TIMESTAMP`      | Data creării contului (default CURRENT_TIMESTAMP) |


### Tabela meetings

| Câmp               | Tip            | Descriere                                  |
|--------------------|-----------------|---------------------------------------------|
| `id`               | `INT`          | **Primary Key**, Auto Increment (ID unic pentru întâlnire)      |
| `student_id`       | `INT`          | Cheie externă către tabelul `users`, ID-ul studentului (nu poate fi nul) |
| `professor_id`     | `INT`          | Cheie externă către tabelul `users`, ID-ul profesorului (nu poate fi nul) |
| `meeting_date`     | `DATETIME`     | Data și ora întâlnirii (nu poate fi nul)                        |
| `duration_minutes` | `INT`          | Durata întâlnirii în minute (implicit 60 minute)                 |
| `status`           | `ENUM('pending', 'confirmed', 'rejected', 'completed', 'cancelled')` | Statusul întâlnirii           |
| `student_message`  | `TEXT`          | Mesajul trimis de student (poate fi nul)                        |
| `professor_response`| `TEXT`         | Răspunsul trimis de profesor (poate fi nul)                      |
| `points_cost`      | `INT`           | Punctele consumate pentru întâlnire (implicit 500 puncte)        |
| `created_at`       | `DATETIME`      | Data și ora când a fost creată întâlnirea (implicit `CURRENT_TIMESTAMP`) |
| `updated_at`       | `DATETIME`      | Data și ora ultimei actualizări (actualizat automat)            |


### Tabela lesson
| **Coloană**        | **Tip**                                         | **Nullable** | **Descriere**                                           |
|--------------------|-------------------------------------------------|--------------|---------------------------------------------------------|
| `id`               | Integer (Cheie primară)                         | Nu           | Identificator unic pentru fiecare lecție               |
| `title`            | String(200)                                     | Nu           | Titlul lecției                                          |
| `description`      | Text                                            | Nu           | Descrierea lecției                                      |
| `content`          | Text                                            | Nu           | Conținutul principal al lecției                         |
| `level`            | Enum ('beginner', 'intermediate', 'advanced')   | Nu           | Nivelul de dificultate al lecției (începător, intermediar, avansat) |
| `category`         | String(100)                                     | Da           | Categoria lecției (ex. Gramatică, Vocabular, Citire)    |
| `professor_id`     | Integer (Cheie externă: `users.id`)             | Nu           | Cheie externă către profesorul care a creat lecția      |
| `duration_minutes` | Integer                                         | Da           | Durata estimată a lecției în minute                     |
| `difficulty`       | Integer (1-5)                                   | Da           | Nivelul de dificultate (de la 1 la 5)                   |
| `rating`           | Float                                           | Da           | Rating-ul mediu al lecției                              |
| `total_ratings`    | Integer                                         | Da           | Numărul total de evaluări ale lecției                   |
| `views`            | Integer                                         | Da           | Numărul de vizualizări ale lecției                      |
| `completions`      | Integer                                         | Da           | Numărul de completări ale lecției                       |
| `status`           | Enum ('draft', 'published', 'archived')         | Nu           | Starea lecției (schiță, publicată, arhivată)            |
| `image_url`        | String(500)                                     | Da           | URL-ul imaginii de previzualizare a lecției             |
| `created_at`       | DateTime                                        | Da           | Data și ora când a fost creată lecția                   |
| `updated_at`       | DateTime                                        | Da           | Data și ora ultimei actualizări a lecției               |
| `professor`        | Relație (User)                                  | Nu           | Relația cu profesorul (creatorul lecției)               |

🔒 Securitate

✅ Parolele sunt criptate cu bcrypt\
✅ Validare server-side pentru toate datele\
✅ Protecție împotriva SQL injection (SQLAlchemy ORM)\
✅ Sessions securizate cu Flask-Login\
✅ Email-uri verificate cu regex

### 🎯 Sprint 2 - Lecții:
✅ Funcționalități Complete:

✅ Model complet cu 15 câmpuri (titlu, descriere, conținut, nivel, vizualizări, dificultate etc.)\
✅ Lista lecții în grid responsive (3 coloane ecran maxim, 2 coloane ecran mediu, 1 coloană ecran mic)\
✅ Filtrare pe 3 niveluri + "Toate"\
✅ Informații complete: profesor, durată, dificultate (stele)\
✅ Categorii (Grammar, Vocabulary, etc.)

Detalii Lecție:

✅ Breadcrumb navigare\
✅ Header complet cu toate informații\
✅ Conținut HTML formatat (liste, paragrafe)\
✅ Sidebar cu statistici detaliate\
✅ Progress bar citire (se umple la scroll)\
✅ Butoane acțiune (Marchează finalizat, Salvează, Înapoi)\
✅ Incrementare automată views

### 🎯 Sprint 3 - Quizuri & Evaluare:
 Funcționalități Complete:

 Model Quiz complet cu un singur răspuns corect sau întrebări cu adevărat/fals\
 Sistem evaluare cu puncte și feedback\
 Calculator de progres utilizator\
 Statistici detaliate per student\
 Dashboard cu overview complet (puncte, lecții, badge-uri, zile consecutive, bazat pe quizuri completate cu 70%)\
 Meetings (întâlniri cu profesorii) - programare și management

### 🎯 Sprint 4 - Gamification & Leaderboard:
 Funcționalități Complete:

 **Sistem de Recompense**
   - Model Reward complet cu status (În așteptare/Revendicat/Expirat), dată câștig și expirare\
   - Generare automată de recompense la depășirea punctelor (200, 500, 1000, 2000)
   - Endpoint admin /api/rewards/generate pentru generare batch
   - Revendicare recompense cu feedback vizual

 **Clasamente (Leaderboard)**
   - Clasament global studenți cu paginație
   - Afișare poziția utilizatorului curent
   - Clasament profesori cu:
     * Calcul scor compus (rating x 100 + lecții x 10 + vizualizări x 0.1)
     * Filtrare pe nivel (Începător/Intermediar/Avansat)
   - Paginație cu butoane Anterior/Următor
   - Statistici detaliate (puncte, lecții completate, rating-uri)

### 🎯Sprint 5 - Funcționalități Profesor:
✅ Funcționalități Complete:

✅ **Gestionare Clase**
   - Creare clase cu cod de acces
   - Alăturare studenți cu cod (join-class)
   - Vizualizare detalii clasă cu studenți
   - Ștergere clasă (admin)

✅ **Sistemul de Feedback**
   - Profesor trimite feedback personalizat
   - Tip feedback: lecție, quiz, general
   - Rating 1-5 stele
   - Mesaj detaliat
   - Studentul vede feedback instant în clasă

✅ **Banca de Întrebări**
   - Profesor crează bănci tematice
   - Adaugă întrebări reutilizabile
   - Organizare per dificultate

✅ **UI/Template-uri**
   - Pagină /class/<id> cu tab-uri (Studenți, Feedback, Setări)
   - Pagină /join-class pentru studenți
   - Pagină /professor-dashboard cu gestionare clase