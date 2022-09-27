fetch('../json/people.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element){
      var fullNamePerson = element["name"];
      var imageId = element["photo"];

      if (element.hasOwnProperty("title"))
        fullNamePerson = element["title"] + ' ' + fullNamePerson;
      if (!element.hasOwnProperty("photo"))
        imageId = 'default.png';

      $('#people-section').append(
        '<div class="teamblock col-md-3 col-sm-6 col-xs-6 filtr-item" data-category="' + element["research_areas"] + "," + element["research_interest_terms"] + '">' +
          '<div class="team-member">'+
            '<div class="portfolio-block member-photo">' +
              '<div style="text-align: center;"><img class="img-fluid" src="images/people/' + imageId + '" alt="' + fullNamePerson + '"></div>' +
              '<div class="caption mask">' +
                '<ul class="clearfix">' +
                  '<li><a href="' + element["homepage"] + '" target="_blank"><i class="tf-ion-link"></i></a></li>' +
                  '<li><a href="' + element["linkedin"] + '" target="_blank"><i class="tf-ion-social-linkedin"></i></a></li>' +
                  '<li><a href="' + element["google_scholar"] + '" target="_blank"><i class="tf-ion-social-google"></i></a></li>' +
                  '<li><a href="' + element["github"] + '" target="_blank"><i class="tf-ion-social-github"></i></a></li>' +
                '</ul>' +
              '</div>' +
            '</div>' +
            '<div class="member-content text-center">' +
              '<a href="single-profile.html?user=' + element["shef_ai_link"] + '"><h3>' + fullNamePerson + ' <span class="bi bi-arrow-bar-right" style="font-size: 1.3rem"></span></h3></a>' +
              '<div><h4>' + element["position"] + '</h4></div>' +
              '<div><h4>' + element["affiliation"] + '</h4></div>' +
              '<br/>' +
              '<div><h4>' + element["research_areas"] + '</h4></div>' +
            '</div>' +
          '</div>' +
        '</div>'
        );
    });
  });