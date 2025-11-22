document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('registerForm');
    const submitBtn = document.getElementById('submitBtn');
    const messageContainer = document.getElementById('message-container');
    
    // Event listener pentru submit-ul formularului
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Colectează datele din formular
        const firstName = document.getElementById('firstName').value.trim();
        const lastName = document.getElementById('lastName').value.trim();
        const email = document.getElementById('email').value.trim().toLowerCase();
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        // Validare client-side
        const validationError = validateForm(firstName, lastName, email, password, confirmPassword);
        if (validationError) {
            showMessage(validationError, 'error');
            return;
        }
        
        // Disable buton și arată loading
        submitBtn.disabled = true;
        submitBtn.classList.add('loading');
        submitBtn.textContent = 'Se înregistrează...';
        
        try {
            // Trimite request către API
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    firstName: firstName,
                    lastName: lastName,
                    email: email,
                    password: password
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Succes - arată mesaj și redirecționează
                showMessage(data.message || 'Cont creat cu succes!', 'success');
                
                // Redirecționează către login după 2 secunde
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            } else {
                // Eroare de la server
                showMessage(data.error || 'A apărut o eroare. Te rugăm să încerci din nou.', 'error');
                resetButton();
            }
            
        } catch (error) {
            console.error('Eroare:', error);
            showMessage('Nu s-a putut conecta la server. Verifică conexiunea la internet.', 'error');
            resetButton();
        }
    });
    
    // Funcție de validare
    function validateForm(firstName, lastName, email, password, confirmPassword) {
        // Verifică câmpuri goale
        if (!firstName || !lastName || !email || !password || !confirmPassword) {
            return 'Toate câmpurile sunt obligatorii!';
        }
        
        // Validare nume (minim 2 caractere)
        if (firstName.length < 2 || lastName.length < 2) {
            return 'Numele și prenumele trebuie să aibă cel puțin 2 caractere!';
        }
        
        // Validare email
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailRegex.test(email)) {
            return 'Adresa de email nu este validă!';
        }
        
        // Validare parolă (minim 6 caractere)
        if (password.length < 6) {
            return 'Parola trebuie să aibă cel puțin 6 caractere!';
        }
        
        // Verifică dacă parolele se potrivesc
        if (password !== confirmPassword) {
            return 'Parolele nu se potrivesc!';
        }
        
        return null; // Nu există erori
    }
    
    // Funcție pentru afișarea mesajelor
    function showMessage(message, type) {
        const icon = type === 'success' ? '✅' : '❌';
        const messageClass = type === 'success' ? 'message-success' : 'message-error';
        
        messageContainer.innerHTML = `
            <div class="message ${messageClass}">
                <span class="message-icon">${icon}</span>
                <span>${message}</span>
            </div>
        `;
        messageContainer.style.display = 'block';
        
        // Scroll la mesaj
        messageContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    // Funcție pentru resetarea butonului
    function resetButton() {
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
        submitBtn.textContent = 'Creează Cont';
    }
    
    // Validare în timp real pentru parolă
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    
    confirmPasswordInput.addEventListener('input', function() {
        if (this.value && passwordInput.value !== this.value) {
            this.setCustomValidity('Parolele nu se potrivesc');
        } else {
            this.setCustomValidity('');
        }
    });
});