document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('filtro');
    const resultadosContainer = document.querySelector('#resultados-container');
    const buscaForm = document.getElementById('busca-form');
    const baseUrl = buscaForm ? buscaForm.getAttribute('data-termos-url') : '/termos';

    // Função de debounce para limitar a frequência das requisições
    function debounce(func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // Função para fazer a requisição AJAX
    function fetchResults(url) {
        if (resultadosContainer) {
            resultadosContainer.innerHTML = '<div class="loading">Carregando...</div>';
        }

        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            const newResultados = doc.querySelector('#resultados-container');
            if (!newResultados) {
                throw new Error('Elemento #resultados-container não encontrado no HTML retornado');
            }

            const newPagination = doc.querySelector('nav[aria-label="Navegação de páginas"]');
            const newModal = doc.querySelector('#deleteModal');

            if (resultadosContainer) {
                resultadosContainer.innerHTML = newResultados.innerHTML;

                const currentPagination = document.querySelector('nav[aria-label="Navegação de páginas"]');
                if (newPagination && currentPagination) {
                    currentPagination.outerHTML = newPagination.outerHTML;
                } else if (newPagination) {
                    resultadosContainer.insertAdjacentHTML('afterend', newPagination.outerHTML);
                } else if (currentPagination) {
                    currentPagination.remove();
                }

                const currentModal = document.querySelector('#deleteModal');
                if (newModal && currentModal) {
                    currentModal.outerHTML = newModal.outerHTML;
                }

                attachPaginationEvents();
            }
        })
        .catch(error => {
            if (resultadosContainer) {
                resultadosContainer.innerHTML = '<div class="error">Erro ao carregar resultados: Ocorreu um problema. Por favor, tente novamente mais tarde.</div>';
            }
            console.error('Erro:', error);
        });
    }

    // Função para lidar com a busca dinâmica (com debounce)
    if (input) {
        const debouncedFetchResults = debounce(function () {
            const busca = input.value;

            const params = new URLSearchParams();
            params.set('busca', busca);
            params.delete('page');

            const url = `${baseUrl}?${params.toString()}`;
            fetchResults(url);
        }, 300);

        input.addEventListener('input', debouncedFetchResults);
    }

    // Função para atribuir eventos de clique aos links de paginação
    function attachPaginationEvents() {
        const paginationLinks = document.querySelectorAll('.pagination .page-link');
        paginationLinks.forEach(link => {
            link.addEventListener('click', function (event) {
                event.preventDefault();
                const url = this.getAttribute('href');
                if (url) {
                    fetchResults(url);
                }
            });
        });
    }

    attachPaginationEvents();
});