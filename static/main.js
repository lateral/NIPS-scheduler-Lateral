$().ready(function() {
	$(document).on('click', '.add-to-schedule', function(event) {
		var event_id = $(event.target).data('id');
		$('#schedule').load('/add', {event_id: event_id});
		$('.add-to-schedule ').fadeOut()
	});
	$(document).on('click', '.remove-from-schedule', function(event) {
		var event_id = $(event.target).data('id');
		$('#schedule').load('/remove', {event_id: event_id});
	});
	$('#search-box').keypress(function(e) {
	    if(e.which == 13) {
		var keywords = $(this).val();
		window.location = '/search?keywords=' + keywords;
	    }
	});
});


