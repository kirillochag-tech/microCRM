// static/js/multiple-upload.js
document.addEventListener('DOMContentLoaded', function() {
    // Обработка множественной загрузки фото
    const photoInputs = document.querySelectorAll('input[type="file"][name^="question_"]');
    
    photoInputs.forEach(input => {
        if (input.type === 'file') {
            // Создаем контейнер для preview фото
            const container = document.createElement('div');
            container.className = 'photo-preview-container mt-2';
            input.parentNode.insertBefore(container, input.nextSibling);
            
            input.addEventListener('change', function(e) {
                container.innerHTML = '';
                const files = e.target.files;
                for (let i = 0; i < files.length && i < 10; i++) {
                    const file = files[i];
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.style.maxWidth = '100px';
                        img.style.maxHeight = '100px';
                        img.style.margin = '5px';
                        container.appendChild(img);
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    });
});