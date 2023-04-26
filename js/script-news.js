fetch('../json/news.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element){
      $('#news-section').append(
        '<article class="col-md-4 col-sm-6 col-xs-12 ">'+
          '<div class="post-item">' + 
            '<div class="media-wrapper news-collection">' + 
              '<img src="images/news/' + element["image"] +'" alt="News-' + element["title"] + '" class="img-fluid">' + 
            '</div>' +
            '<div class="content">' +
              '<p class="news-item"><i class="bi bi-calendar"> ' + element["date"] +'</i></p>'+
              '<h3><a href=single-news.html?id=' + element["id"] + '>' + element["title"] + '</a></h3>' +
              '<p class="system-link">' + element["summary"] + '</p>' + 
              '<a class="btn btn-main" href=single-news.html?id=' + element["id"] + '>Read more</a>' + 
            '</div>' +
          '</div>' +  
        '</article>');
    });
  });