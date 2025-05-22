// Auto-hide flash messages after 5 seconds
$(document).ready(function() {
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
});


function manterSessãoAtiva() {
    $.get("{{ url_for('main.keep_session_alive') }}");
}
setInterval(manterSessãoAtiva, 300000); 