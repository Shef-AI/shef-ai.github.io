fetch('../json/research.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element){
      var igGroup = element["ig-groups"].split(",");
      var igGroupTags = '<ul class="feature-list system-style"><h5>Interest Groups:</h5>';
      igGroup.forEach(function(item){
        igGroupTags += '<li> <i class="tf-ion-android-checkmark-circle"></i>' + item + '</li>';
      });
      igGroupTags += '</ul>';

      $('#research-section').append(
        '<div class="col-md-6 col-sm-4 research-box">' +
          '<div class="research-item">' +
            '<a href="#"><img src="images/research/' + element["image"] + '" alt="Reseach-Group-' + element["title"] + '" class="img-fluid"></a>' +
              '<div class="research-content">' +
                '<p><h3>' + element["title"] + '</h3></p>' +
                '<p>' + element["description"] + '</p>' +
                igGroupTags +
              '</div>' +
          '</div>' +
        '</div>' 
      );
    });
  });