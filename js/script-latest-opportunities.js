fetch('../json/opportunities.json')
  .then(response => response.json())
  .then(data => {
    for (var i = 0; i < data.length && i < 3; i++) {
        block_style = "color-bg-2";
        button_style = "btn-main-2"
        if (i % 2 === 0) {
          block_style = "color-bg";
          button_style = "btn-main"
        }
        var newsElement = data[i];
        $('#latest-opportunities-section').append(
            '<div class="col-lg-4 col-sm-6 mb-4 mb-lg-0 service-block ' + block_style + '">' +
                '<div class="p-4 text-center">' +
                    '<a href="single-opportunity.html?id=' + newsElement["id"] + '"><h3>' + newsElement["title"] + '</h3></a>' +
                    '<i class="bi bi-alarm" > ' + newsElement["date"] + '</i>' +
                    '<p>' + newsElement["summary"] + '</p>' +
                    '<a class="btn ' + button_style + '" href="single-opportunity.html?id=' + newsElement["id"] + '">Read More</a>' +
                '</div>' +
            '</div>');
    }
  });