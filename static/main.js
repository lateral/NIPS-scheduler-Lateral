$().ready(function() {

	// Add to Schedule

	$(document).on('click', '.add-to-schedule', function(event) {
		var event_id = $(event.target).data('id');
		$('#schedule').load('/add', {event_id: event_id});
		$('.event-' + event_id + ' .add-to-schedule').hide();
		$('.event-' + event_id + ' .remove-from-schedule').fadeIn('fast');
		$('#right-panel .event-' + event_id + ' .schedule-remove').hide()
	});

	// Remove from Schedule

	$(document).on('click', '.remove-from-schedule', function(event) {
		var event_id = $(event.target).data('id');
		$('#schedule').load('/remove', { event_id: event_id });
		$('.event-' + event_id + ' .remove-from-schedule').hide();
		$('#right-panel .event-' + event_id + ' .add-to-schedule').fadeIn('fast');
	});

	// Search

	$('#search-box').keypress(function(e) {
	    if(e.which == 13) {
		var keywords = $(this).val();
		window.location = '/search?keywords=' + keywords;
	    }
	});

	$('.search-button').click(function() {
	    var keywords = $('#search-box').val();
	    window.location = '/search?keywords=' + keywords;
	});

	// Related content switcher

	$('.event-single-related h4 span').click(function(e) {
  	var target = $(this).data('target');
  	$('.related-source').fadeOut()
   	$('#' + target).delay(200).fadeIn()
   	$('.event-single-related h4 span').removeClass("show")
   	$(this).addClass("show")

  });
});


