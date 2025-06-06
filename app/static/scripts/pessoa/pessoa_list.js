document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('filtro');
    const resultadosContainer = document.querySelector('#resultados-container');
    const buscaForm = document.getElementById('busca-form');
    const baseUrl = buscaForm ? buscaForm.getAttribute('data-pessoas-url') : '/pessoas';

    console.log('Base URL:', baseUrl); // Log para depuração

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
        // Mostra um indicador de carregamento
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
            // Criar um elemento temporário para parsear o HTML retornado
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            // Extrair o conteúdo do #resultados-container
            const newResultados = doc.querySelector('#resultados-container');
            if (!newResultados) {
                throw new Error('Elemento #resultados-container não encontrado no HTML retornado');
            }

            // Extrair a navegação de paginação
            const newPagination = doc.querySelector('nav[aria-label="Navegação de páginas"]');

            if (resultadosContainer) {
                // Atualizar o #resultados-container com o novo conteúdo
                resultadosContainer.innerHTML = newResultados.innerHTML;

                // Atualizar a navegação de paginação (se existir)
                const currentPagination = document.querySelector('nav[aria-label="Navegação de páginas"]');
                if (newPagination && currentPagination) {
                    currentPagination.outerHTML = newPagination.outerHTML;
                } else if (newPagination) {
                    // Se não houver paginação atual, mas houver nova paginação, adicionar após o #resultados-container
                    resultadosContainer.insertAdjacentHTML('afterend', newPagination.outerHTML);
                } else if (currentPagination) {
                    // Se não houver nova paginação, mas houver paginação atual, remover
                    currentPagination.remove();
                }

                // Reatribuir eventos de clique para os novos links de paginação
                attachPaginationEvents();
            }
        })
        .catch(error => {
            if (resultadosContainer) {
                resultadosContainer.innerHTML = '<div class="error">Erro ao carregar resultados: Ocorreu um problema. Por favor, tente novamente mais tarde.</div>';
            }
        });
    }

    // Função para lidar com a busca dinâmica (com debounce)
    if (input) {
        const debouncedFetchResults = debounce(function () {
            const busca = input.value;

            // Monta os parâmetros da URL
            const params = new URLSearchParams();
            params.set('busca', busca);
            params.delete('page');

            // Faz a requisição para a primeira página com a busca
            const url = `${baseUrl}?${params.toString()}`;
            fetchResults(url);
        }, 300); // 300ms de espera antes de fazer a requisição

        input.addEventListener('input', debouncedFetchResults);
    }

    // Função para atribuir eventos de clique aos links de paginação
    function attachPaginationEvents() {
        const paginationLinks = document.querySelectorAll('.pagination .page-link');
        paginationLinks.forEach(link => {
            link.addEventListener('click', function (event) {
                event.preventDefault(); // Impede o comportamento padrão do link
                const url = this.getAttribute('href');
                if (url) {
                    fetchResults(url);
                }
            });
        });
    }

    // Atribuir eventos de clique aos links de paginação iniciais
    attachPaginationEvents();
});