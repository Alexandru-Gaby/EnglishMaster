// Logică pentru gestionarea întâlnirilor

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
}

function respondMeeting(meetingId, action) {
    const modal = document.getElementById('responseModal');
    const backdrop = document.getElementById('modalBackdrop');
    const modalTitle = document.getElementById('modalTitle');
    const linkGroup = document.getElementById('linkGroup');
    
    document.getElementById('meeting_id_response').value = meetingId;
    document.getElementById('action_response').value = action;
    
    if (action === 'confirm') {
        modalTitle.textContent = '✅ Confirmă Întâlnirea';
        linkGroup.style.display = 'block';
    } else {
        modalTitle.textContent = '❌ Respinge Întâlnirea';
        linkGroup.style.display = 'none';
    }
    
    modal.style.display = 'block';
    backdrop.style.display = 'block';
}

function closeResponseModal() {
    document.getElementById('responseModal').style.display = 'none';
    document.getElementById('modalBackdrop').style.display = 'none';
    document.getElementById('responseForm').reset();
}

async function cancelMeeting(meetingId) {
    if (!confirm('Ești sigur că vrei să anulezi această întâlnire? Punctele vor fi returnate.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/meetings/${meetingId}/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
            
            // Reîncarcă pagina după 2 secunde
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showMessage(data.error, 'error');
        }
        
    } catch (error) {
        console.error('Eroare:', error);
        showMessage('Nu s-a putut anula întâlnirea.', 'error');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const responseForm = document.getElementById('responseForm');
    
    if (responseForm) {
        responseForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const meetingId = document.getElementById('meeting_id_response').value;
            const action = document.getElementById('action_response').value;
            const message = document.getElementById('response_message').value;
            const meetingLink = document.getElementById('meeting_link').value;
            
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            
            submitBtn.disabled = true;
            submitBtn.textContent = 'Se trimite...';
            
            try {
                const response = await fetch(`/api/meetings/${meetingId}/respond`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        action: action,
                        message: message,
                        meeting_link: meetingLink
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showMessage(data.message, 'success');
                    closeResponseModal();
                    
                    // Reîncarcă pagina după 2 secunde
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    showMessage(data.error, 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }
                
            } catch (error) {
                console.error('Eroare:', error);
                showMessage('Nu s-a putut trimite răspunsul.', 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }
    
    // Închide modal cu ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeResponseModal();
        }
    });
});