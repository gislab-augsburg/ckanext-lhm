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
