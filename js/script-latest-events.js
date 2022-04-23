import data from "../json/events.json" assert { type: "json" };

for (var i = 0; i < data.length && i < 3; i++) {
    var eventElement = data[i];
    $('#latest-events-section').append(
      '<div class="col-md-6 col-sm-4">' +
        '<img loading="lazy" src="images/events/' + eventElement["image"] + '" alt="Event-' + eventElement["title"] + '" class="img-fluid">' +
        '<p>' +
            '<ul class="list-inline">' +
                '<i class="bi bi-calendar"> ' + eventElement["date"] + '&nbsp;&nbsp;&nbsp;</i>' +
                '<i class="bi bi-clock"> ' + eventElement["time"] + '&nbsp;&nbsp;&nbsp;</i>' +
                '<i class="bi bi-alarm"> ' + eventElement["duration"] + ' Hours</i>' +
            '</ul>' +
            '<ul class="list-inline">' +
                '<i class="bi bi-geo-alt"> ' + eventElement["location"] + '</i>' +
            '</ul>' +
            (eventElement["virtual"] ? 
              ('<ul class="list-inline"><i class="bi bi bi-camera-video"><a href="' + eventElement["virtual"] + '"> Virtual Meeting</a></i></ul>') : 
              '<br/>'
            )+  
        '</p>' +
        '<p><h3><a href="single-event.html?id=' + eventElement["id"] + '" style="color: black">' + eventElement["title"] + '</a></h3></p>' +
        '<p>' + eventElement["summary"] + '</p>' +
        '<a class="btn btn-main" href="single-event.html?id=' + eventElement["id"] + '">Read more</a>' +
      '</div>' 
    );
}