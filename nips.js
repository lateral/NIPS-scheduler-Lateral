$().ready(function() {

	$('.add-to-schedule').on('click', function() {
		var event_id = $(this).siblings('.event_id').text();
		alert(event_id);
	});
});
