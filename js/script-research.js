import dataResearch from "../json/research.json" assert { type: "json" };
import dataSoftware from "../json/software.json" assert { type: "json" };

for (var i = 0; i < dataResearch.length && i < 3; i++) {
  var newsElement = dataResearch[i];
  $('#research-section').append(
    '<div class="col-md-4 col-sm-4">' +
      '<a href="#"><img src="images/research/' + newsElement["image"] + '" alt="Reseach-Group-' + newsElement["title"] + '" class="img-fluid"></a>' +
      '<p><h3>' + newsElement["title"] + '</h3></p>' +
      '<p>' + newsElement["description"] + '</p>' +
    '</div>' 
  );
}

for (var i = 0; i < dataSoftware.length && i < 3; i++) {
  var newsElement = dataSoftware[i];
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