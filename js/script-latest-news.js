fetch('../json/news.json')
  .then(response => response.json())
  .then(data => {
    for (var i = 0; i < data.length && i < 3; i++) {
        var newsElement = data[i];
        $('#latest-news-section').append(
            '<article class="col-lg-4 col-md-6">' + 
                '<div class="post-item">' +
                    '<div class="media-wrapper latest-news">' +
                        '<img loading="lazy" src="images/news/' + newsElement["image"] + '" alt="News-' + newsElement["title"] + '" class="img-fluid">' +
                    '</div>' +
                    '<div class="content">' +
                        '<p><i class="bi bi-calendar"> ' + newsElement["date"] +'</i></p>'+
                        '<h3><a href="single-news.html?id=' + newsElement["id"] + '">' + newsElement["title"] + '</a></h3>' +
                        '<p>' + newsElement["summary"] + '</p>' +
                        '<a class="btn btn-main" href="single-news.html?id=' + newsElement["id"] + '">Read more</a>' +
                    '</div>' +
                '</div>' +
            '</article>'
        );
    }
  });