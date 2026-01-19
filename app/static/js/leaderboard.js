// Leaderboard state
let studentsPage = 1;
let studentsPerPage = 25;
let currentProfessorLevel = 'all';

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadStudentsLeaderboard(1);
    loadProfessorsLeaderboard();
});


function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(function(tab) {
        tab.classList.remove('active');
    });
    
    // Deactivate all buttons
    document.querySelectorAll('.tab-btn').forEach(function(btn) {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    const tabElement = document.getElementById(tabName + '-tab');
    if (tabElement) {
        tabElement.classList.add('active');
    }
    
    // Activate selected button
    event.target.classList.add('active');
}

function filterProfessors(level) {
    currentProfessorLevel = level;
    
    // Update active filter button
    document.querySelectorAll('.filter-btn').forEach(function(btn) {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    loadProfessorsLeaderboard();
}

function loadStudentsLeaderboard(page) {
    if (!page) page = 1;
    studentsPage = page;
    
    const url = '/api/leaderboard/global?page=' + page + '&per_page=' + studentsPerPage;
    
    fetch(url)
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                displayStudentsLeaderboard(
                    data.leaderboard,
                    data.current_user_rank,
                    data.total_users,
                    data.page,
                    data.per_page
                );
            } else {
                console.error('Error loading leaderboard:', data.error);
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
        });
}

function displayStudentsLeaderboard(leaderboard, userRank, totalUsers, page, perPage) {
    const tbody = document.getElementById('studentsTableBody');
    
    if (!leaderboard || leaderboard.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="no-data">Niciun student găsit</td></tr>';
        return;
    }
    
    let html = '';
    const startRank = (page - 1) * perPage + 1;
    
    leaderboard.forEach(function(user, index) {
        const rank = startRank + index;
        const isCurrentUser = user.is_current_user ? 'current-user' : '';
        const rankDisplay = rank === 1 ? '🥇' : (rank === 2 ? '🥈' : (rank === 3 ? '🥉' : rank));
        
        html += '<tr class="' + isCurrentUser + '">';
        html += '<td class="rank-col">' + rankDisplay + '</td>';
        html += '<td class="name-col">' + user.name + (user.is_current_user ? ' (Tu)' : '') + '</td>';
        html += '<td class="points-col">' + user.points + '</td>';
        html += '<td class="lessons-col">' + user.lessons_completed + '</td>';
        html += '</tr>';
    });
    
    tbody.innerHTML = html;
    
    // Render pagination
    renderStudentsPagination(totalUsers, page, perPage);
    
    // Show user rank if exists
    const userRankEl = document.getElementById('userRankNumber');
    if (userRankEl && userRank) {
        userRankEl.textContent = userRank;
    }
}

// Render pagination controls
function renderStudentsPagination(totalUsers, currentPage, perPage) {
    const container = document.getElementById('studentsPagination');
    const totalPages = Math.ceil(totalUsers / perPage);
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    if (currentPage > 1) {
        html += '<button class="btn-pagination" onclick="loadStudentsLeaderboard(' + (currentPage - 1) + ')">← Anterior</button>';
    } else {
        html += '<button class="btn-pagination" disabled>← Anterior</button>';
    }
    
    // Page info
    html += '<span class="page-info">Pagina ' + currentPage + ' din ' + totalPages + '</span>';
    
    // Next button
    if (currentPage < totalPages) {
        html += '<button class="btn-pagination" onclick="loadStudentsLeaderboard(' + (currentPage + 1) + ')">Următor →</button>';
    } else {
        html += '<button class="btn-pagination" disabled>Următor →</button>';
    }
    
    container.innerHTML = html;
}

function loadProfessorsLeaderboard() {
    let url = '/api/leaderboard/professors';
    
    if (currentProfessorLevel && currentProfessorLevel !== 'all') {
        url += '?level=' + currentProfessorLevel;
    }
    
    fetch(url)
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                displayProfessorsLeaderboard(data.leaderboard);
            } else {
                console.error('Error loading professors:', data.error);
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
        });
}

function displayProfessorsLeaderboard(professors) {
    const container = document.getElementById('professorsGrid');
    
    if (!professors || professors.length === 0) {
        container.innerHTML = '<div class="no-data" style="grid-column: 1/-1; padding: 40px; text-align: center;">Niciun profesor găsit</div>';
        return;
    }
    
    let html = '';
    
    professors.forEach(function(professor, index) {
        const medal = index === 0 ? '🥇' : (index === 1 ? '🥈' : (index === 2 ? '🥉' : ''));
        const rating = professor.rating || 0;
        const lessonsCount = professor.lessons_created || 0;
        const viewsCount = professor.lessons_views || 0;
        
        html += '<div class="professor-card">';
        html += '<div class="professor-header">';
        html += '<div class="professor-rank">' + (medal || (index + 1)) + '</div>';
        html += '<div class="professor-name">' + professor.name + '</div>';
        html += '</div>';
        
        html += '<div class="professor-level">' + (professor.level || 'Nespecificat') + '</div>';
        
        html += '<div class="professor-stats">';
        html += '<div class="stat"><strong>Rating:</strong> ' + rating.toFixed(1) + ' ⭐</div>';
        html += '<div class="stat"><strong>Lecții:</strong> ' + lessonsCount + ' 📚</div>';
        html += '<div class="stat"><strong>Vizualizări:</strong> ' + viewsCount + ' 👁️</div>';
        html += '</div>';
        
        html += '</div>';
    });
    
    container.innerHTML = html;
}