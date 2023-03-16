// Get the value of "id" in "https://shef-ai.github.io/opportunities.html?id=some_value"
const params = new Proxy(new URLSearchParams(window.location.search), {
  get: (searchParams, prop) => searchParams.get(prop),
});

fetch('../json/opportunities.json')
  .then(response => response.json())
  .then(data => {
        // Search the json file to find the element by id
        var element = data.find(element => element["id"] === params.id);

        if (element) {
            $('#opportunity-section').append(
                '<div class="post-content">' +
                    '<h3>' + element["title"] + '</h3>' +
                    '<ul class="list-inline">' +
                        '<i class="bi bi-alarm"> ' + element["date"] + ' <br/></i>' +
                    '</ul>' +
                    '<p>' + element["body"] + '</p>' +
                    '<ul class="post-content-share list-inline">' +
                        '<li class="list-inline-item">' +
                            '<a href="#"><i class="tf-ion-social-twitter"></i></a>' +
                        '</li>' +
                        '<li class="list-inline-item">' +
                            '<a href="#"><i class="tf-ion-social-linkedin"></i></a>' +
                        '</li>' +
                        '<li class="list-inline-item">' +
                            '<a href="#"><i class="tf-ion-social-facebook"></i></a>' +
                        '</li>' +
                        '<li class="list-inline-item">' +
                            '<a href="#"><i class="tf-ion-social-skype"></i></a>' +
                        '</li>' +
                    '</ul>' +
                '</div>'
            );
        }
        else {
            window.location.href = "../404.html"
        }
  });