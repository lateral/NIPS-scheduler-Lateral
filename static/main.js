$().ready(function() {

	// Add to Schedule

	$(document).on('click', '.add-to-schedule', function(event) {
		var event_id = $(event.target).data('id');
		$('#schedule').load('/add', {event_id: event_id});
		$(event.target).fadeOut("fast")
		$(event.target).siblings('.remove-from-schedule').fadeIn("fast")
	});

	// Remove from Schedule

	$(document).on('click', '.remove-from-schedule', function(event) {
		var event_id = $(event.target).data('id');
		$('#schedule').load('/remove', {event_id: event_id});
		$(event.target).fadeOut("fast")
		$(event.target).siblings('.add-to-schedule').fadeIn("fast")
	});

	// Search

	$('#search-box').keypress(function(e) {
	    if(e.which == 13) {
		var keywords = $(this).val();
		window.location = '/search?keywords=' + keywords;
	    }
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


