import data from "../json/people.json" assert { type: "json" };

data.forEach(function(element){
  $('#people-section').append(
    '<div class="col-md-3 col-sm-6 col-xs-6 filtr-item" data-category="mix, ' + element["areas"] + '">' +
      '<div class="team-member">'+
        '<div class="portfolio-block member-photo">' +
          '<img class="img-fluid" src="images/people/' + element["image"] + '" alt="Academic-Staff-' + element["name"] + '">' +
          '<div class="caption mask">' +
            '<ul class="clearfix">' +
              '<li><a href="' + element["homepage"] + '" target="_blank"><i class="tf-ion-link"></i></a></li>' +
              '<li><a href="' + element["linkedin"] + '" target="_blank"><i class="tf-ion-social-linkedin"></i></a></li>' +
              '<li><a href="' + element["scholar"] + '" target="_blank"><i class="tf-ion-social-google"></i></a></li>' +
              '<li><a href="' + element["github"] + '" target="_blank"><i class="tf-ion-social-github"></i></a></li>' +
            '</ul>' +
          '</div>' +
        '</div>' +
        '<div class="member-content text-center">' +
          '<h3>' + element["name"] + '</h3>' +
          '<span>' + element["rank"] + '</span>' +
          '<p>' + element["bio"]  + '</p>' +
        '</div>' +
      '</div>' +
    '</div>'
    );
});