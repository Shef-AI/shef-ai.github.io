fetch('../json/jobs.json')
  .then(response => response.json())
  .then(data => {
    for (var i = 0; i < data.length && i < 3; i++) {
      var newsElement = data[i];
      block_style = "color-bg-2";
      button_style = "btn-main-2"
      if (i % 2 === 0) {
        block_style = "color-bg";
        button_style = "btn-main"
      }
      $('#jobs-section').append(
        '<div class="col-lg-4 col-sm-6 mb-4 mb-lg-0">' +
          '<div class="service-block p-4 ' + block_style + ' text-center">' +
            '<a href="single-job.html?id=' + newsElement["id"] + '"><h3>' + newsElement["title"] + '</h3></a>' +
            '<i class="bi bi-geo" > ' + newsElement["location"] + '</i>' +
            '<p>' + newsElement["summary"] + '</p>' +
            '<a class="btn ' + button_style + '" href="single-job.html?id=' + newsElement["id"] + '">Read More</a>' +
          '</div>' +
        '</div>'
      );
    }
  });

  fetch('../json/funds.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element, index){
      block_style = "color-bg-2";
      button_style = "btn-main-2"
      if (index % 2 === 0) {
        block_style = "color-bg";
        button_style = "btn-main"
      }
      $('#funds-section').append(
        '<div class="grallery-block p-4 ' + block_style + ' text-center">' +
          '<a href="single-fund.html?id=' + element["id"] + '"><h3>' + element["title"] + '</h3></a>' +
          '<p>' + element["summary"] + '</p>' +
          '<a class="btn ' + button_style + '" href="single-fund.html?id=' + element["id"] + '">Read More</a>'+
        '</div>'
        );
        
    });
    $('.company-gallery').slick('refresh');
  });