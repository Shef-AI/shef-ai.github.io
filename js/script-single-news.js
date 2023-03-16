// Get the value of "id" in "https://shef-ai.github.io/news.html?id=some_value"
const params = new Proxy(new URLSearchParams(window.location.search), {
  get: (searchParams, prop) => searchParams.get(prop),
});

fetch('../json/news.json')
  .then(response => response.json())
  .then(data => {
        // Search the json file to find the element by id
        var element = data.find(element => element["id"] === params.id);

        if (element) {
            $('#news-section').append(
                '<div class="post-image">' + 
                    '<img class="img-fluid w-100" src="images/news/' + element["image"] + '" alt=News-"' + element["title"] + '">' + 
                '</div>' +
                '<div class="post-content">' +
                    '<ul class="list-inline">' +
                        '<i class="bi bi-calendar"> ' + element["date"] + '</i>' +
                    '</ul>' +
                    '<h3>' + element["title"] + '</h3>' +
                    '<p>' + element["body"] + '</p>' + 
                    '<ul class="post-content-share list-inline">' +
                        '<li class="list-inline-item">' +
                            '<a href="#"> <i class="tf-ion-social-twitter"></i> </a>' +
                        '</li>' +
                        '<li class="list-inline-item">' +
                            '<a href="#"> <i class="tf-ion-social-linkedin"></i> </a>' +
                        '</li>' +
                        '<li class="list-inline-item">' +
                            '<a href="#"> <i class="tf-ion-social-facebook"></i> </a>' +
                        '</li>' +
                        '<li class="list-inline-item">' +
                            '<a href="#"> <i class="tf-ion-social-skype"></i> </a>' +
                        '</li>' +
                    '</ul>' +
                '</div>' 
            );
        }
        else {
            window.location.href = "../404.html"
        }

        for (var i = 0; i < data.length && i < 3; i++) {
            var newsElement = data[i];
            $('#latest-news').append(
                '<li class="widget-post-list-item">' +
                    '<div class="widget-post-image">' +
                        '<a href="single-news.html?id=' + newsElement["id"] + '"> <img src="images/news/' + newsElement["image"] + '" alt="News-' + newsElement["title"] + '"></a>' +
                    '</div>' +
                    '<div class="widget-post-content">' +
                        '<a href="single-news.html?id=' + newsElement["id"] + '"><h5>' + newsElement["title"] + '</h5></a>' + 
                        '<h6>' + newsElement["date"] + '</h6>' +
                    '</div>' +
                '</li>' 
            );
        }
  });