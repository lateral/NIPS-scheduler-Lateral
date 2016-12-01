$(function() {

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

  $('#search-box').keyup(function() {
    if($(this).val() != '') {
      $('button.search-button').removeClass('disabled');
    } else {
      $('button.search-button').addClass('disabled');
    }
  });

  // Mobile Switcher

  $('.switcher .left').click(function() {
	  $('#right-panel').fadeOut()
	  $('.switcher .right p').addClass("show")
	  $('#left-panel').fadeIn()
	  $('#download-schedule').fadeIn()
	  $('.switcher .left p').addClass("show")
	});

	$('.switcher .right').click(function() {
	  $('#left-panel').fadeOut()
	  $('#download-schedule').fadeOut()
	  $('.switcher .left p').removeClass("show")
	  $('#right-panel').fadeIn()
	  $('.switcher .right p').removeClass("show")
	});

  // Date filter
  function getHash() {
    var hash = window.location.hash.replace(/^#!/, '').split('&');
    if (hash.length == 1) {
      // window.location.hash = '#!date=all&type=all';
      history.replaceState(undefined, undefined, "#!date=all&type=all")
      hash = window.location.hash.replace(/^#!/, '').split('&');
    }
    return [hash[0].replace('date=', ''), hash[1].replace('type=', '')];
  }

  function updateFiltersFromHash() {
    var hash = getHash();
    var dateVal = hash[0];
    var typeVal = hash[1];
    if(dateVal == 'all' && typeVal == 'all') {
      $('#events .event-result').show();
    } else {
      var dateString = dateVal.replace('_', ' ');
      $('#events .event-result').each(function(val){
        var eventDay = $(this).find('.day').text();
        if (typeVal == 'all') {
          $(this).toggle(eventDay == dateString);
        } else if (dateVal == 'all') {
          $(this).toggle($(this).find('.event_type').hasClass(typeVal));
        } else {
          $(this).toggle(eventDay == dateString && $(this).find('.event_type').hasClass(typeVal));
        }
      });
    }
    $('.no-events').toggle(!$('#events .event-result:visible').length);
  }

  $(window).bind('hashchange', updateFiltersFromHash);
  updateFiltersFromHash();
  var hash = getHash();

  $('#filter-date select').val(hash[0]);
  $('#filter-date select').change(function(event) {
    var val = $(this).val();
    window.location.hash = '#!date=' + val + '&type=' + getHash()[1];
  });

  $('#filter-type select').val(hash[1]);
  $('#filter-type select').change(function(event) {
    var val = $(this).val();
    window.location.hash = '#!date=' + getHash()[0] + '&type=' + val;
  });

  $('.reset-filters').on('click', function(){
    $('#filter-date select').val('all');
    $('#filter-type select').val('all');
    window.location.hash = '#!date=all&type=all';
  });

});


