// MessMate Core Client Script

document.addEventListener('DOMContentLoaded', function () {
  // 1. Auto-dismiss alerts after 5 seconds
  document.querySelectorAll('.alert:not(.alert-permanent)').forEach(function (alertEl) {
    setTimeout(function () {
      if (window.bootstrap) {
        const instance = bootstrap.Alert.getOrCreateInstance(alertEl);
        instance.close();
      }
    }, 5000);
  });

  // 2. Active navbar link highlighting
  var currentPath = window.location.pathname;
  document.querySelectorAll('.app-navbar .nav-link').forEach(function (link) {
    var href = link.getAttribute('href');
    if (href) {
      var hrefPath = href.split('?')[0];
      if (hrefPath === currentPath || (hrefPath !== '/' && currentPath.indexOf(hrefPath) === 0)) {
        link.classList.add('active');
      }
    }
  });

  // 3. Mobile menu auto-collapse on link click
  var navCollapse = document.getElementById('navMain');
  if (navCollapse && window.bootstrap) {
    navCollapse.querySelectorAll('.nav-link').forEach(function (link) {
      link.addEventListener('click', function () {
        if (navCollapse.classList.contains('show')) {
          var collapseInst = bootstrap.Collapse.getOrCreateInstance(navCollapse);
          collapseInst.hide();
        }
      });
    });
  }

  // 4. Client-side fast filter for meals accordion or member tables
  var memberSearchInput = document.getElementById('memberFilterInput');
  if (memberSearchInput) {
    memberSearchInput.addEventListener('input', function () {
      var q = this.value.toLowerCase().trim();
      document.querySelectorAll('.filterable-member').forEach(function (item) {
        var name = (item.getAttribute('data-member-name') || '').toLowerCase();
        if (!q || name.indexOf(q) !== -1) {
          item.style.display = '';
        } else {
          item.style.display = 'none';
        }
      });
    });
  }
});
