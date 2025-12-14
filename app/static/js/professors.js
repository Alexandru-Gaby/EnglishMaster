// Logică pentru programarea întâlnirilor

function openBookingModal(professorId, professorName) {
    document.getElementById('professor_id').value = professorId;
    document.getElementById('professor_name').value = professorName;
    
    // Setează data minimă la acum
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('meeting_date').min = now.toISOString().slice(0, 16);
    
    document.getElementById('bookingModal').style.display = 'block';
    document.getElementById('modalBackdrop').style.display = 'block';
}

function closeBookingModal() {
    document.getElementById('bookingModal').style.display = 'none';
    document.getElementById('modalBackdrop').style.display = 'none';
    document.getElementById('bookingForm').reset();
}

function showMessage(message, type) {
    const container = document.getElementById('message-container');
    const icon = type === 'success' ? '✅' : '❌';
    const messageClass = type === 'success' ? 'message-success' : 'message-error';
    
    container.innerHTML = `
        <div class="message ${messageClass}">
            <span class="message-icon">${icon}</span>
            <span>${message}</span>
        </div>
    `;
    container.style.display = 'block';
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // Ascunde mesajul după 5 secunde
    setTimeout(() => {
        container.style.display = 'none';
    }, 5000);
}

document.addEventListener('DOMContentLoaded', function() {
    const bookingForm = document.getElementById('bookingForm');
    
    bookingForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitBtn = document.getElementById('submitBooking');
        const originalText = submitBtn.textContent;
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Se trimite...';
        
        const formData = {
            professor_id: parseInt(document.getElementById('professor_id').value),
            meeting_date: document.getElementById('meeting_date').value,
            message: document.getElementById('message').value
        };
        
        try {
            const response = await fetch('/api/meetings/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                showMessage(data.message, 'success');
                closeBookingModal();
                
                // Actualizează numărul de puncte în pagină
                const pointsElements = document.querySelectorAll('.page-header strong');
                if (pointsElements.length > 0) {
                    pointsElements[0].textContent = data.remaining_points;
                }
                
                // Redirecționează la meetings după 2 secunde
                setTimeout(() => {
                    window.location.href = '/meetings';
                }, 2000);
            } else {
                showMessage(data.error, 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
            
        } catch (error) {
            console.error('Eroare:', error);
            showMessage('Nu s-a putut trimite cererea. Verifică conexiunea la internet.', 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
    
    // Închide modal cu ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeBookingModal();
        }
    });
});