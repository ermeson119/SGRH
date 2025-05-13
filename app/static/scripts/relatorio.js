document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('busca-form');
    const resultadosContainer = document.querySelector('#lista-funcionarios');

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        params.delete('page');

        // Mostra um indicador de carregamento
        if (resultadosContainer) {
            resultadosContainer.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Carregando...</span></div></div>';
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
                resultadosContainer.innerHTML = '<div class="alert alert-danger">Erro ao carregar resultados.</div>';
            }
        });
    });

    // Atualiza a URL com os parâmetros de busca
    function updateURL() {
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        window.history.pushState({}, '', `/relatorio/completo?${params.toString()}`);
    }

    // Atualiza a URL quando os campos do formulário mudam
    form.querySelectorAll('input, select').forEach(element => {
        element.addEventListener('change', updateURL);
    });
});

document.querySelectorAll('.collapse').forEach(collapse => {
    collapse.addEventListener('show.bs.collapse', function () {
        const button = document.querySelector(`button[data-bs-target="#${this.id}"] svg use`);
        button.setAttribute('xlink:href', '#chevron-up');
    });
    collapse.addEventListener('hide.bs.collapse', function () {
        const button = document.querySelector(`button[data-bs-target="#${this.id}"] svg use`);
        button.setAttribute('xlink:href', '#chevron-down');
    });
});