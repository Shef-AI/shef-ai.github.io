fetch('../json/research.json')
  .then(response => response.json())
  .then(data => {
    for (var i = 0; i < data.length && i < 3; i++) {
      var newsElement = data[i];
      $('#research-section').append(
        '<div class="col-md-4 col-sm-4">' +
          '<a href="#"><img src="images/research/' + newsElement["image"] + '" alt="Reseach-Group-' + newsElement["title"] + '" class="img-fluid"></a>' +
          '<p><h3>' + newsElement["title"] + '</h3></p>' +
          '<p>' + newsElement["description"] + '</p>' +
        '</div>' 
      );
    }
  });

fetch('../json/software.json')
  .then(response => response.json())
  .then(data => {
    for (var i = 0; i < data.length && i < 3; i++) {
      var newsElement = data[i];
      $('#software-section').append(
        '<div class="col-md-4 col-sm-6 col-xs-12">' +
          '<div class="pricing-item">' +
            '<div class="price-title">' +
              '<strong class="value">' + newsElement["title"] + '</strong>' +
              '<p>' + newsElement["description"] + '</p>' +
            '</div>' +
            '<a class="btn btn-main" href="' + newsElement["link"] + '" target="_blank">MORE</a>' +
          '</div>' +
        '</div>' 
        );
    }
  });