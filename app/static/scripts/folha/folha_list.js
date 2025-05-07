// Função para limitar a frequência de requisições
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Função para buscar resultados
function buscarResultados() {
    const form = document.getElementById('busca-form');
    const url = form.dataset.folhasUrl;
    const busca = document.getElementById('filtro').value;
    const data = document.getElementById('data').value;
    const status = document.getElementById('status').value;
    const container = document.getElementById('resultados-container');
    
    // Mostra o spinner de carregamento
    container.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Carregando...</span>
            </div>
        </div>
    `;
    
    // Faz a requisição AJAX
    fetch(`${url}?busca=${encodeURIComponent(busca)}&data=${encodeURIComponent(data)}&status=${encodeURIComponent(status)}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Erro na requisição');
        }
        return response.text();
    })
    .then(html => {
        // Atualiza o conteúdo da tabela
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newContainer = doc.getElementById('resultados-container');
        container.innerHTML = newContainer.innerHTML;
        
        // Atualiza a paginação
        const pagination = doc.querySelector('.pagination');
        if (pagination) {
            const currentPagination = document.querySelector('.pagination');
            if (currentPagination) {
                currentPagination.outerHTML = pagination.outerHTML;
            } else {
                document.querySelector('.table-responsive').after(pagination);
            }
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                Erro ao buscar resultados. Por favor, tente novamente.
            </div>
        `;
    });
}

// Adiciona os event listeners
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('busca-form');
    const filtro = document.getElementById('filtro');
    const data = document.getElementById('data');
    const status = document.getElementById('status');
    
    // Usa debounce para limitar as requisições
    const buscarComDebounce = debounce(buscarResultados, 300);
    
    // Event listeners para mudanças nos campos
    filtro.addEventListener('input', buscarComDebounce);
    data.addEventListener('change', buscarComDebounce);
    status.addEventListener('change', buscarComDebounce);
    
    // Previne o envio do formulário
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        buscarResultados();
    });
}); 