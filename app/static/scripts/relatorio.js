document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('filtro');
    const resultadosContainer = document.querySelector('#resultados-container');

    input.addEventListener('input', function () {
        const busca = input.value;

        // Monta os parâmetros da URL
        const params = new URLSearchParams();
        params.set('busca', busca);
        params.delete('page'); 

        // Mostra um indicador de carregamento (opcional)
        if (resultadosContainer) {
            resultadosContainer.innerHTML = '<div class="loading">Carregando...</div>';
        }

        // Faz uma requisição assíncrona para buscar os resultados
        fetch(`/relatorio/completo?${params.toString()}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest' 
            }
        })
        .then(response => response.text()) 
        .then(html => {
            if (resultadosContainer) {
                resultadosContainer.innerHTML = html;
            }
        })
        .catch(error => {
            console.error('Erro ao buscar resultados:', error);
            if (resultadosContainer) {
                resultadosContainer.innerHTML = '<div class="error">Erro ao carregar resultados.</div>';
            }
        });
    });
});