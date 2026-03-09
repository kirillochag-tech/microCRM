// Функция для инициализации обработчиков
function initAcknowledgeForms() {
    document.querySelectorAll('.acknowledge-form').forEach(form => {
        if (form.dataset.initialized) return; // Защита от повторной инициализации
        form.dataset.initialized = 'true';
        
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            if (!submitBtn) return;
            
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Обработка...';
            
            const formData = new FormData(this);
            const announcementId = this.action.split('/').slice(-2)[0];
            const cardElement = document.getElementById(`announcement-card-${announcementId}`);

            try {
                const response = await fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'success' && cardElement) {
                        // Получаем текущие классы элемента
                        const originalClasses = cardElement.className;
                        const newCard = document.createElement('div');
                        newCard.className = originalClasses; // Сохраняем оригинальные классы
                        newCard.id = `announcement-card-${announcementId}`;
                        newCard.innerHTML = `
                            <div class="card">
                                <div class="card-body">
                                    <h6 class="card-title text-primary">${cardElement.querySelector('.card-title').textContent}</h6>
                                    <p class="card-text">${cardElement.querySelector('.card-text').textContent}</p>
                                    <small class="text-muted d-block mb-1">
                                        ${cardElement.querySelector('small').innerHTML}
                                    </small>
                                    <span class="badge bg-success">Подтверждено</span>
                                </div>
                            </div>
                        `;
                        cardElement.replaceWith(newCard);
                    }
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            } catch (error) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
                alert('Ошибка при подтверждении.');
            }
        });
    });
}

// Запускаем инициализацию после полной загрузки страницы
document.addEventListener('DOMContentLoaded', function() {
    initAcknowledgeForms();
    // Повторяем инициализацию через короткую задержку для карусели
    setTimeout(initAcknowledgeForms, 500);
});