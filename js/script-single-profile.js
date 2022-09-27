// Get the value of "user" in "https://sheffieldai.github.io/single-profile.html?user=some_value"
const params = new Proxy(new URLSearchParams(window.location.search), {
  get: (searchParams, prop) => searchParams.get(prop),
});

fetch('../json/people.json')
  .then(response => response.json())
  .then(data => {
        // Search the json file to find the element by shef_ai_link
        var element = data.find(element => element["shef_ai_link"] === params.user);

        if (element) {
            var fullNamePerson = element["name"];
            var imageId = element["photo"];
      
            if (element.hasOwnProperty("title"))
              fullNamePerson = element["title"] + ' ' + fullNamePerson;
            if (!element.hasOwnProperty("photo"))
              imageId = 'default.png';

            var interestsTerms = element["research_interest_terms"].split(",");
            var interestsTermsTags = '<ul>';
            interestsTerms.forEach(function(item){
                interestsTermsTags += '<li>' + item + '</li>';
            });
            interestsTermsTags += '</ul>';

            var areasTerms = element["research_areas"].split(",");
            var areasTermsTags = '';
            areasTerms.forEach(function(item){
                areasTermsTags += '<a class="btn rounded-pill btn-outline-primary mr-2 mb-2" href="#" role="button">' + item + '</a>';
            });

            $('#profile-section').append(
                '<div class="col-md-5 single-member text-center">'+
                    '<img class="img-fluid" src="images/people/' + imageId + '" alt="' + fullNamePerson + '">'+
                    '<div class="info-block mt-4">'+
                        '<h3 class="mb-0">' + fullNamePerson + '</h3>'+
                        '<p>' + element["position"] + '</p>'+
                        '<h5>' + element["affiliation"] + '</h5>'+
      
                        '<ul class="list-inline mt-4">'+
                            '<li class="list-inline-item"><a href="' + element["homepage"] + '" target="_blank"><i class="tf-ion-link" style="font-size: 40px"></i></a></li>'+
                            '<li class="list-inline-item"><a href="' + element["linkedin"] + '" target="_blank"><i class="tf-ion-social-linkedin" style="font-size: 40px"></i></a></li>'+
                            '<li class="list-inline-item"><a href="' + element["google_scholar"] + '" target="_blank"><i class="tf-ion-social-google" style="font-size: 40px"></i></a></li>'+
                            '<li class="list-inline-item"><a href="' + element["github"]+ '" target="_blank"><i class="tf-ion-social-github" style="font-size: 38px"></i></a></li>'+

                        '</ul>'+
                    '</div><br/>'+
                    areasTermsTags +
                '</div>'+
                '<div class="col-md-7">'+
                    (element["short_biography"] ? 
                        ('<h2>Biography</h2>'+
                            '<div class="divider my-4"></div>'+
                            '<p>' + element["short_biography"] + '</p><br/>') : 
                        '<br/>'
                    )+ 
                    '<h2>Research Interests</h2>' +
                    '<div class="divider my-4"></div>'+
                    (element["research_interest_summary"] ? ('<p>' + element["research_interest_summary"] + '</p>') : '')+
                    interestsTermsTags +
                    '<br/>' +
                '</div>'
            );
        }
        else {
            window.location.href = "../404.html"
        }
  });