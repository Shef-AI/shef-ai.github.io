import data from "../json/research.json" assert { type: "json" };

data.forEach(function(element){
  $('#research-section').append(
      '<div class="col-md-6 col-sm-4">' +
        '<a href="#"><img src="images/research/' + element["image"] + '" alt="Reseach-Group-' + element["title"] + '" class="img-fluid"></a>' +
        '<p><h3>' + element["title"] + '</h3></p>' +
        '<p>' + element["description"] + '</p>' +
      '</div>' 
    );
});