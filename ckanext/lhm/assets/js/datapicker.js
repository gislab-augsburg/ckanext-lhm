class DatePickerInitializer {
  constructor(inputSelector) {
    this.inputSelector = inputSelector;
  }

  initialize() {
    const $input = $(this.inputSelector);

    $input.datepicker({
      dateFormat: 'yy/mm/dd',
      changeMonth: true,
      changeYear: true
    });

    const currentDate = $.datepicker.formatDate('yy/mm/dd', new Date());
    $input.val(currentDate);
  }
}

$(function() {
  // Use event delegation for '.datepicker-init' elements
  $(document).on('focus', '.datepicker-init', function() {
    const inputSelector = '#' + this.id;
    const datePickerInitializer = new DatePickerInitializer(inputSelector);
    datePickerInitializer.initialize();
  });
});
