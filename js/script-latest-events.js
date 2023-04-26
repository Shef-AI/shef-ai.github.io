fetch('../json/events.json')
  .then(response => response.json())
  .then(data => {
    for (var i = 0; i < data.length && i < 2; i++) {
      var eventElement = data[i];
      $('#latest-events-section').append(
        '<article class="col-md-6 col-sm-4">' + 
            '<div class="post-item">' +
                '<div class="media-wrapper latest-news">' +
                    '<img loading="lazy" src="images/events/' + eventElement["image"] + '" alt="Event-' + eventElement["title"] + '" class="img-fluid">' +
                '</div>' +
                '<div class="content">' +
                    '<p>' +
                        '<ul class="list-inline system-style">' +
                            '<i class="bi bi-calendar"> ' + eventElement["date"] + '&nbsp;&nbsp;&nbsp;</i>' +
                            '<i class="bi bi-clock"> ' + eventElement["time"] + '&nbsp;&nbsp;&nbsp;</i>' +
                            '<i class="bi bi-alarm"> ' + eventElement["duration"] + ' Hours</i>' +
                        '</ul>' +
                        '<ul class="list-inline system-style">' +
                            '<i class="bi bi-geo-alt"> ' + eventElement["location"] + '</i>' +
                        '</ul>' +
                        (eventElement["virtual"] ? 
                          ('<ul class="list-inline system-style system-link-virtual"><i class="bi bi bi-camera-video"><a href="' + eventElement["virtual"] + '"> Virtual Participation Link</a></i></ul>') : 
                          '<br/>'
                        )+  
                    '</p>' +
                    '<h3><a href="single-event.html?id=' + eventElement["id"] + '">' + eventElement["title"] + '</a></h3>' +
                    '<p class="system-link">' + eventElement["summary"] + '</p>' +
                    '<a class="btn btn-main" href="single-event.html?id=' + eventElement["id"] + '">Read more</a>' +
                '</div>' +
            '</div>' +
        '</article>'
      );
    }
  });