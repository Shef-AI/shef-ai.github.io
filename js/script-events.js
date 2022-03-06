import data from "../json/events.json" assert { type: "json" };

data.content.forEach(function(element){
  $('#events-section').append(
    '<div class="row">' +
      '<div class="col-md-6">' +
        '<a href="single-event.html?id=' + element["id"] + '">' +
          '<img class="img-fluid" src="images/events/' + element["image"] +'" alt="Event-' + element["title"] + '">' +
        '</a>' +
      '</div>' +
      '<div class="col-md-6">' +
        '<h2><a style="color: black;" href="single-event.html?id=' + element["id"] + '">' + element["title"] + '</a></h2>' +
        '<p>' +
          '<ul class="list-inline">' +
            '<i class="bi bi-calendar"> ' + element["date"] + '&nbsp;&nbsp;&nbsp;</i>' +
            '<i class="bi bi-clock"> ' + element["time"] + '</i>' +
          '</ul>' +
          '<ul class="list-inline">' +
            '<i class="bi bi-geo-alt"> ' + element["location"] + '</i>' +
          '</ul>' +
        '</p>' +
        '<p>' + element["body"] + '</p>' +
      '</div>' +
    '</div>' +
    '<p></p><p></p>');
});
