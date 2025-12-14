document.addEventListener('DOMContentLoaded', function() {
    // Handle announcement acknowledgment forms
    const acknowledgeForms = document.querySelectorAll('.acknowledge-form');
    
    acknowledgeForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent default form submission
            
            const formData = new FormData(form);
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            
            // Disable button and show loading state
            submitButton.disabled = true;
            submitButton.textContent = 'Обработка...';
            
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Update UI to show acknowledged status
                    const parentDiv = form.closest('.announcement-item');
                    if (parentDiv) {
                        const buttonContainer = form.parentElement; // Get the parent container of the form
                        if (buttonContainer) {
                            buttonContainer.innerHTML = '<div class="mt-2"><span class="badge bg-success">Подтверждено</span></div>';
                        }
                        
                        // Optional: Remove the acknowledge button and show 'Acknowledged' badge
                        // Instead of reloading immediately, just update the visual state
                        // We can refresh the whole widget area after a delay if needed
                        setTimeout(() => {
                            // Reload the page to update all announcement statuses
                            window.location.reload();
                        }, 500); // Small delay to allow UI update
                    }
                } else {
                    console.error('Error:', data.message);
                    // Re-enable button on error
                    submitButton.disabled = false;
                    submitButton.textContent = originalText;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Re-enable button on error
                submitButton.disabled = false;
                submitButton.textContent = originalText;
                
                // Show error to user
                alert('Ошибка при подтверждении прочтения объявления. Пожалуйста, попробуйте снова.');
            });
        });
    });
});