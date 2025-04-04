document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('filtro');
    let timeout = null;

    input.addEventListener('input', function () {
        clearTimeout(timeout);

        timeout = setTimeout(function () {
            const busca = input.value;
            const url = new URL(window.location.href);

            url.searchParams.set('busca', busca);
            url.searchParams.delete('page');

            window.location.href = url.toString();
        }, 500);
    });
});
