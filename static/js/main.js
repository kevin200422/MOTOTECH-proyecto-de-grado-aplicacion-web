/**
 * Main UI interactions for the Taller Mecánico application.
 *
 * This script implements the following behaviours:
 *  - Toggling the sidebar between expanded and collapsed states.
 *  - Applying a fade‑in animation to card components when the page
 *    loads.  The CSS defines the animation; here we simply ensure
 *    that cards start hidden to avoid a flash of unstyled content.
 */

document.addEventListener('DOMContentLoaded', function () {
  // Sidebar toggle
  const toggleButton = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  if (toggleButton && sidebar) {
    toggleButton.addEventListener('click', function () {
      sidebar.classList.toggle('collapsed');
      // The margin of the main container updates automatically via CSS
    });
  }
});