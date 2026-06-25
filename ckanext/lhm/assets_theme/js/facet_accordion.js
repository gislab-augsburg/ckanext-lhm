(function () {
  function setToggleState(root) {
    var details = root.querySelectorAll('.lhm-facet-details');
    var toggle = root.querySelector('[data-lhm-facet-toggle-all]');

    if (!toggle || !details.length) {
      return;
    }

    var allOpen = Array.prototype.every.call(details, function (item) {
      return item.open;
    });

    toggle.setAttribute('aria-expanded', allOpen ? 'true' : 'false');
    toggle.classList.toggle('is-open', allOpen);
  }

  function filterFacet(input) {
    var details = input.closest('.lhm-facet-details');

    if (!details) {
      return;
    }

    var query = input.value.trim().toLowerCase();
    var items = details.querySelectorAll('.nav-facet .nav-item');

    Array.prototype.forEach.call(items, function (item) {
      var label = item.getAttribute('data-lhm-facet-label') || item.textContent || '';
      item.hidden = query !== '' && label.toLowerCase().indexOf(query) === -1;
    });
  }

  document.addEventListener('click', function (event) {
    var toggle = event.target.closest('[data-lhm-facet-toggle-all]');

    if (!toggle) {
      return;
    }

    var root = toggle.closest('.lhm-facet-accordion');

    if (!root) {
      return;
    }

    var details = root.querySelectorAll('.lhm-facet-details');
    var shouldOpen = Array.prototype.some.call(details, function (item) {
      return !item.open;
    });

    Array.prototype.forEach.call(details, function (item) {
      item.open = shouldOpen;
    });

    setToggleState(root);
  });

  document.addEventListener('input', function (event) {
    if (event.target.matches('.lhm-facet-search')) {
      filterFacet(event.target);
    }
  });

  document.addEventListener('toggle', function (event) {
    if (!event.target.matches('.lhm-facet-details')) {
      return;
    }

    var root = event.target.closest('.lhm-facet-accordion');

    if (root) {
      setToggleState(root);
    }
  }, true);
})();
