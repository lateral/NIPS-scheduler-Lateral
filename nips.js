$().ready(function() {

	$('.add-to-schedule').on('click', function() {
		var event_id = $(this).siblings('.event_id').text();
		$('#schedule').load('/add', {event_id: event_id});
	});
	$('.remove-from-schedule').on('click', function() {
		var event_id = $(this).siblings('.event_id').text();
		$('#schedule').load('/remove', {event_id: event_id});
	});
});
