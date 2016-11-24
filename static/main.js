$().ready(function() {
	$(document).on('click', '.add-to-schedule', function(event) {
		var event_id = $(event.target).data('id');
		$('#schedule').load('/add', {event_id: event_id});
		$(event.target).fadeOut("fast")
		$(event.target).siblings('.remove-from-schedule').fadeIn("fast")
	});

	$(document).on('click', '.remove-from-schedule', function(event) {
		var event_id = $(event.target).data('id');
		$('#schedule').load('/remove', {event_id: event_id});
		$(event.target).fadeOut("fast")
		$(event.target).siblings('.add-to-schedule').fadeIn("fast")
	});

	$('#search-box').keypress(function(e) {
	    if(e.which == 13) {
		var keywords = $(this).val();
		window.location = '/search?keywords=' + keywords;
	    }
	});
});


