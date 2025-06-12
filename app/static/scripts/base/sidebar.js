document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mainContent = document.getElementById('main-content');
    const bootstrapNavbarToggler = document.getElementById('bootstrapNavbarToggler');
    
    // Recupera o estado do menu do localStorage
    const isSidebarCollapsedInitial = localStorage.getItem('sidebarCollapsed') === 'true';
    
    // Função para atualizar o estado do menu
    function updateSidebarState(isCollapsed) {
        if (window.innerWidth >= 768) {
            // Desktop
            sidebar.classList.toggle('collapsed', isCollapsed);
            sidebar.classList.remove('show');
            document.body.classList.toggle('sidebar-collapsed', isCollapsed);
        } else {
            // Mobile
            sidebar.classList.toggle('show', !isCollapsed);
            sidebar.classList.remove('collapsed');
            document.body.classList.remove('sidebar-collapsed');
        }
    }
    
    // Aplica o estado inicial
    updateSidebarState(isSidebarCollapsedInitial);
    
    // Adiciona o evento de clique ao botão personalizado do sidebar
    sidebarToggle.addEventListener('click', function(event) {
        event.stopPropagation();
        const currentlyCollapsed = sidebar.classList.contains('collapsed') || !sidebar.classList.contains('show');
        updateSidebarState(!currentlyCollapsed);
        localStorage.setItem('sidebarCollapsed', !currentlyCollapsed);
    });
    
    // Adiciona evento de clique ao toggler do Bootstrap (para mobile)
    if (bootstrapNavbarToggler) {
        bootstrapNavbarToggler.addEventListener('click', function(event) {
            event.stopPropagation();
            const isCurrentlyShown = sidebar.classList.contains('show');
            updateSidebarState(isCurrentlyShown);
            localStorage.setItem('sidebarCollapsed', !isCurrentlyShown);
        });
    }
    
    // Adiciona evento de redimensionamento da janela
    window.addEventListener('resize', function() {
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        updateSidebarState(isCollapsed);
    });
    
    // Fecha o menu ao clicar fora dele em dispositivos móveis
    document.addEventListener('click', function(event) {
        if (window.innerWidth < 768 && 
            !sidebar.contains(event.target) && 
            !sidebarToggle.contains(event.target) && 
            sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
            localStorage.setItem('sidebarCollapsed', 'true');
        }
    });
}); 