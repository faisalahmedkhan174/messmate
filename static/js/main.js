// MessMate shared client-side helpers.
// Page-specific auto-save logic (meals) lives inline in its template's script block.

document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss flash alerts after a few seconds for a cleaner mobile UI.
  document.querySelectorAll('.alert').forEach(function (alertEl) {
    setTimeout(function () {
      if (window.bootstrap) {
        const instance = bootstrap.Alert.getOrCreateInstance(alertEl);
        instance.close();
      }
    }, 6000);
  });
});
