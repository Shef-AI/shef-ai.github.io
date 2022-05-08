fetch('../json/jobs.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element, index){
      block_style = "color-bg-2";
      button_style = "btn-main-2"
      if (index % 2 === 0) {
        block_style = "color-bg";
        button_style = "btn-main"
      }
      $('#jobs-section').append(
        '<div class="col-lg-4 col-sm-6 mb-4 mb-lg-0">' +
          '<div class="service-block p-4 ' + block_style + ' text-center">' +
            '<a href="single-job.html?id=' + element["id"] + '"><h3>' + element["title"] + '</h3></a>' +
            '<i class="bi bi-geo" > ' + element["location"] + '</i>' +
            '<p>' + element["summary"] + '</p>' +
            '<a class="btn ' + button_style + '" href="single-job.html?id=' + element["id"] + '">Read More</a>' +
          '</div>' +
        '</div>');
    });
  });