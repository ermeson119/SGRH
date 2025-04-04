document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('filtro');
    input.addEventListener('input', function () {
        const termo = input.value.toLowerCase();
        const cards = document.querySelectorAll('.funcionario-card');

        cards.forEach(function (card) {
            const nome = card.querySelector('.nome').textContent.toLowerCase();
            card.style.display = nome.includes(termo) ? '' : 'none';
        });
    });
});