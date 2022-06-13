fetch('../json/people.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element){
      $('#people-section').append(
        '<div class="teamblock col-md-3 col-sm-6 col-xs-6 filtr-item" data-category="' + element["areas"] + "," + element["interests"] + '">' +
          '<div class="team-member">'+
            '<div class="portfolio-block member-photo">' +
              '<div style="text-align: center;"><img class="img-fluid" src="images/people/' + element["image"] + '" alt="Academic-Staff-' + element["name"] + '"></div>' +
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
              '<a data-toggle="collapse" data-target="#col' + element["id"] + '">' +
                '<h3>' + element["name"] + ' <span class="bi bi-plus-square" style="font-size: 1rem"></span></h3>' +
              '</a>' +
              '<span>' + element["rank"] + '</span>' +
              '<div id="col' + element["id"]  + '" class="collapse" data-parent="#accordion">' +
                '<div class="card-body">' + element["bio"] + '</div>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>'
        );
    });
  });