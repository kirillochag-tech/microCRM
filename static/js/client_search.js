document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('id_client');
    const resultsDiv = document.getElementById('client-list');
    const hiddenInput = document.getElementById('selected_client_id');

    if (!input || !resultsDiv || !hiddenInput) return;

    input.addEventListener('input', async function () {
        const query = this.value.trim();
        resultsDiv.innerHTML = '';
        resultsDiv.style.display = 'none';

        if (query.length < 2) return;

        try {
            // Используем исправленный API-эндпоинт из tasks/urls.py
            const response = await fetch(`/tasks/autocomplete_clients/?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                console.error('Ошибка поиска клиентов');
                return;
            }
            const clients = await response.json();
            if (clients.length === 0) return;

            resultsDiv.innerHTML = clients.map(client =>
                `<div onclick="selectClient(${client.id}, '${client.name.replace(/'/g, "\\'")}')">
                    <strong>${client.name}</strong>
                    ${client.address ? `<br><small>${client.address}</small>` : ''}
                </div>`
            ).join('');

            resultsDiv.style.display = 'block';
        } catch (err) {
            console.error('Ошибка сети:', err);
        }
    });

    window.selectClient = function (id, name) {
        input.value = name;
        hiddenInput.value = id;
        resultsDiv.style.display = 'none';
    };

    document.addEventListener('click', function (e) {
        if (!input.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.style.display = 'none';
        }
    });
});