document.addEventListener('DOMContentLoaded', function() {
    const clientInput = document.getElementById('id_client');
    const clientList = document.getElementById('client-list');
    const clientInputContainer = document.getElementById('client-input-container');
    
    if (clientInput && clientList) {
        let searchTimeout = null;
        
        // Function to perform search
        function performSearch(query) {
            if (query.length < 2) {
                clientList.innerHTML = '';
                clientList.style.display = 'none';
                return;
            }
            
            fetch(`/api/clients/search/?q=${encodeURIComponent(query)}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                clientList.innerHTML = '';
                
                if (data && data.length > 0) {
                    data.forEach(client => {
                        const item = document.createElement('div');
                        item.className = 'client-item';
                        item.textContent = client.name;
                        item.dataset.clientId = client.id;
                        item.dataset.clientName = client.name;
                        
                        item.addEventListener('click', function() {
                            clientInput.value = this.dataset.clientName;
                            document.getElementById('selected_client_id').value = this.dataset.clientId;
                            clientList.style.display = 'none';
                        });
                        
                        clientList.appendChild(item);
                    });
                    clientList.style.display = 'block';
                } else {
                    const noResultsItem = document.createElement('div');
                    noResultsItem.className = 'client-item-message';
                    noResultsItem.textContent = 'Клиенты не найдены';
                    clientList.appendChild(noResultsItem);
                    clientList.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Ошибка:', error);
                clientList.innerHTML = '<div class="client-item-error">Произошла ошибка при поиске</div>';
                clientList.style.display = 'block';
            });
        }
        
        // Handle input with debouncing to improve performance
        // Note: Search happens automatically on input (live search), so search button is not needed
        clientInput.addEventListener('input', function() {
            const query = this.value.trim();
            
            // Clear the previous timeout
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            
            // Set a new timeout to delay the search
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300); // 300ms delay
        });
        
        
        
        document.addEventListener('click', function(e) {
            if (!clientInputContainer.contains(e.target)) {
                clientList.style.display = 'none';
            }
        });
    }
    
    
});