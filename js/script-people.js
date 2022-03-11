import data from "../json/people.json" assert { type: "json" };

data.content.forEach(function(element){
  $('#people-section').append(
    '<div class="col-md-4 col-sm-6">' +
      '<div class="team-member text-center">' +
        '<div class="member-photo">' +
          '<img class="img-fluid" src="images/people/' + element["image"] + '" alt="Academic-Staff-' + element["name"] + '">' +
          '<div class="mask">' +
            '<ul class="clearfix">' +
              '<li><a href="#"><i class="tf-ion-social-facebook"></i></a></li>' +
              '<li><a href="#"><i class="tf-ion-social-twitter"></i></a></li>' +
              '<li><a href="#"><i class="tf-ion-social-google-outline"></i></a></li>' +
              '<li><a href="#"><i class="tf-ion-social-dribbble"></i></a></li>' +
            '</ul>' +
          '</div>' +
        '</div>' + 

        '<div class="member-content">' +
          '<h3>' + element["name"] + '</h3>' +
          '<span>' + element["rank"] + '</span>' +
          '<p>' + element["bio"]  + '</p>' +
        '</div>' +
      '</div>' +
    '</div>' 
    );
});