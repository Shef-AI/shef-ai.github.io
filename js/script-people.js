fetch('../json/people.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element){
      var fullNamePerson = element["name"];
      var imageId = element["image"];

      if (element.hasOwnProperty("title"))
        fullNamePerson = element["title"] + ' ' + fullNamePerson;
      if (!element.hasOwnProperty("image"))
        imageId = 'default.png';

      $('#people-section').append(
        '<div class="teamblock col-md-3 col-sm-6 col-xs-6 filtr-item" data-category="' + element["research_area"] + "," + element["research_interests_terms"] + '">' +
          '<div class="team-member">'+
            '<div class="portfolio-block member-photo">' +
              '<div style="text-align: center;"><img class="img-fluid" src="images/people/' + imageId + '" alt="' + fullNamePerson + '"></div>' +
              '<div class="caption mask">' +
                '<ul class="clearfix">' +
                  '<li><a href="' + element["homepage"] + '" target="_blank"><i class="tf-ion-link"></i></a></li>' +
                  '<li><a href="' + element["linkedin"] + '" target="_blank"><i class="tf-ion-social-linkedin"></i></a></li>' +
                  '<li><a href="' + element["googlescholar"] + '" target="_blank"><i class="tf-ion-social-google"></i></a></li>' +
                  '<li><a href="' + element["github"] + '" target="_blank"><i class="tf-ion-social-github"></i></a></li>' +
                '</ul>' +
              '</div>' +
            '</div>' +
            '<div class="member-content text-center">' +
              '<a href="single-profile.html?user=' + element["shef_ai_link"] + '"><h4>' + fullNamePerson + '</h4></a>' +
              '<div>' + element["position"] + '</div>' +
              '<div>' + element["affiliation"] + '</div>' +
              '<a data-toggle="collapse" data-target="#col' + element["id"] + '">' +
                '<h3><span class="bi bi-plus-square" style="font-size: 1rem"></span></h3>' +
              '</a>' +
              '<div id="col' + element["id"]  + '" class="collapse" data-parent="#accordion">' +
                (element["short_biography"] ? 
                  ('<div class="card-body">' + element["short_biography"] + '</div>') : 
                  '<br/>'
                )+
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>'
        );
    });
  });