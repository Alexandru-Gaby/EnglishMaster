// Funcție pentru afișarea/ascunderea parolelor
function initPasswordToggles() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    
    passwordInputs.forEach(input => {
        // Verifică dacă există deja un toggle
        if (input.nextElementSibling?.classList.contains('password-toggle')) {
            return;
        }
        
        // Creează butonul de toggle
        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'password-toggle';
        toggleBtn.innerHTML = '👁️';
        toggleBtn.title = 'Arată/Ascunde parola';
        
        // Adaugă event listener
        toggleBtn.addEventListener('click', function() {
            if (input.type === 'password') {
                input.type = 'text';
                toggleBtn.innerHTML = '👁️‍🗨️';
            } else {
                input.type = 'password';
                toggleBtn.innerHTML = '👁️';
            }
        });
        
        // Inserează butonul după input
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(toggleBtn);
    });
}

// Funcție pentru validarea în timp real a formularelor
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input[required]');
        
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (!this.value.trim()) {
                    this.classList.add('error');
                } else {
                    this.classList.remove('error');
                }
            });
            
            input.addEventListener('input', function() {
                if (this.classList.contains('error') && this.value.trim()) {
                    this.classList.remove('error');
                }
            });
        });
    });
}

// Funcție pentru animații smooth scroll
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
}

// Funcție pentru tracking-ul activității utilizatorului (opțional)
function trackUserActivity() {
    // Salvează timpul ultimei activități
    let lastActivity = Date.now();
    
    ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
        document.addEventListener(event, () => {
            lastActivity = Date.now();
        });
    });
    
    // Verifică inactivitatea la fiecare 5 minute
    setInterval(() => {
        const inactiveTime = Date.now() - lastActivity;
        // 30 minute de inactivitate
        if (inactiveTime > 30 * 60 * 1000) {
            console.log('Utilizator inactiv de 30 minute');
            // Aici poți adăuga logică pentru logout automat
        }
    }, 5 * 60 * 1000);
}

// Inițializează toate funcționalitățile când DOM-ul e gata
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ EnglishMaster - JavaScript loaded');
    
    // Inițializează funcționalitățile
    initPasswordToggles();
    initFormValidation();
    initSmoothScroll();
    trackUserActivity();
    
    // Log pentru debug (elimină în producție)
    if (window.location.hostname === 'localhost') {
        console.log('🔧 Development mode active');
    }
});

// Export funcții utilitare (pentru a fi folosite în alte fișiere)
window.EnglishMaster = {
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
};