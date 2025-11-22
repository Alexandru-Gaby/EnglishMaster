document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('loginForm');
    const submitBtn = document.getElementById('submitBtn');
    const messageContainer = document.getElementById('message-container');
    
    // Event listener pentru submit-ul formularului
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Colectează datele din formular
        const email = document.getElementById('email').value.trim().toLowerCase();
        const password = document.getElementById('password').value;
        
        // Validare client-side
        if (!email || !password) {
            showMessage('Email și parola sunt obligatorii!', 'error');
            return;
        }
        
        // Validare email
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailRegex.test(email)) {
            showMessage('Adresa de email nu este validă!', 'error');
            return;
        }
        
        // Disable buton și arată loading
        submitBtn.disabled = true;
        submitBtn.classList.add('loading');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Se autentifică...';
        
        try {
            // Trimite request către API
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Succes - salvează user și redirecționează
                showMessage(data.message || 'Autentificare reușită!', 'success');
                
                // Salvează informații despre user (opțional)
                if (data.user) {
                    localStorage.setItem('user', JSON.stringify(data.user));
                }
                
                // Redirecționează către dashboard după 1 secundă
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000);
            } else {
                // Eroare de la server
                showMessage(data.error || 'Email sau parolă incorectă!', 'error');
                resetButton(originalText);
            }
            
        } catch (error) {
            console.error('Eroare:', error);
            showMessage('Nu s-a putut conecta la server. Verifică conexiunea la internet.', 'error');
            resetButton(originalText);
        }
    });
    
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
    function resetButton(originalText) {
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
        submitBtn.textContent = originalText;
    }
    
    // Auto-completare email din localStorage (dacă există)
    const savedEmail = localStorage.getItem('lastEmail');
    if (savedEmail) {
        document.getElementById('email').value = savedEmail;
    }
    
    // Salvează email-ul la submit pentru auto-completare viitoare
    form.addEventListener('submit', function() {
        const email = document.getElementById('email').value.trim();
        if (email) {
            localStorage.setItem('lastEmail', email);
        }
    });
});