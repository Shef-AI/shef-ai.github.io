fetch('../json/events.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element){
      $('#events-section').append(
        '<div class="row">' +
          '<div class="col-md-6 event-collection">' +
            '<a href="single-event.html?id=' + element["id"] + '">' +
              '<img class="img-fluid" src="images/events/' + element["image"] +'" alt="Event-' + element["title"] + '">' +
            '</a>' +
          '</div>' +
          '<div class="col-md-6">' +
            '<h2><a style="color: black;" href="single-event.html?id=' + element["id"] + '">' + element["title"] + '</a></h2>' +
            '<p>' +
              '<ul class="list-inline system-style">' +
                '<i class="bi bi-calendar"> ' + element["date"] + '&nbsp;&nbsp;&nbsp;</i>' +
                '<i class="bi bi-clock"> ' + element["time"] + '&nbsp;&nbsp;&nbsp;</i>' +
                '<i class="bi bi-alarm"> ' + element["duration"] + ' Hours</i>' +
              '</ul>' +
              '<ul class="list-inline system-style">' +
                '<i class="bi bi-geo-alt"> ' + element["location"] + '</i>' +
              '</ul>' +
              (element["virtual"] ? 
                ('<ul class="list-inline system-style"><i class="bi bi bi-camera-video"><a href="' + element["virtual"] + ' "> Virtual Participation Link</a><br/></i></ul>') : 
                '<br/>'
              )+  
            '</p>' +
            '<p>' + element["summary"] + '</p>' +
          '</div>' +
        '</div>' +
        '<p></p><p></p>');
    });
  });