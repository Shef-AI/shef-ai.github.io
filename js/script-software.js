fetch('../json/software.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element){

      var languages = element["languages"].split(",");
      var language_list = '<ul class="system-style">';
      for (let i = 0; i < languages.length; i++) {
        language_list += '<li><i class="tf-ion-ios-arrow-forward"></i>' + languages[i] + '</li>';
      }
      language_list += '</ul>'
    
      $('#software-section').append(
        '<div class="col-md-4 col-sm-6 col-xs-12 pricing-table-box">' +
          '<div class="pricing-item">' +
            '<div class="price-title">' +
              '<strong class="value">' + element["title"] + '</strong>' +
              '<p>' + element["description"] + '</p>' +
            '</div>' +
    
            '<h6>Languages</h6>' +
            language_list+
    
            '<a class="btn btn-main" href="' + element["link"] + '" target="_blank">MORE</a>' +
          '</div>' +
        '</div>' 
        );
    });
  });