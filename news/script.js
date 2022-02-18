import data from "./news.json" assert { type: "json" };

data.content.forEach(function(element){
  $('#news-section').append(
    '<article class="col-md-4 col-sm-6 col-xs-12 ">'+
      '<div class="post-item">' + 
        '<div class="media-wrapper">' + 
          '<img src="images/news/' + element["image"] +'" alt="amazing caves coverimage" class="img-fluid">' + 
        '</div>' +
        '<div class="content">' +
          '<p><i class="bi bi-calendar"> ' + element["date"] +'</i></p>'+
          '<h3><a href="' + element["link"] + '.html">' + element["title"] + '</a></h3>' +
          '<p>' + element["body"] + '</p>' + 
          '<a class="btn btn-main" href="' + element["link"] + '.html">Read more</a>' + 
        '</div>' +
      '</div>' +  
    '</article>');
});