ckan.module("lhm-module", function ($, _) {
  "use strict";
  return {
    options: {
      debug: false,
    },

    initialize: function () {},
  };
});

document.addEventListener('DOMContentLoaded', function() {
  // Find the hidden form within the parent form using a query selector
  var hiddenForm = document.querySelector('#organization-datasets-search-form');
  // Submit the form if found
  if (hiddenForm) {
      // Prevent the default form submission behavior
      hiddenForm.addEventListener('submit', function(event) {
          event.preventDefault(); // Prevent the default form submission
          // Perform any additional actions here if needed
      });

      // Submit the form programmatically
      hiddenForm.submit();
  }
});
