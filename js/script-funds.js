fetch('../json/funds.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element, index){
      block_style = "color-bg-2";
      button_style = "btn-main-2"
      if (index % 2 === 0) {
        block_style = "color-bg";
        button_style = "btn-main"
      }
      $('#funds-section').append(
        '<div class="grallery-block p-4 ' + block_style + ' text-center">' +
          '<a href="single-fund.html?id=' + element["id"] + '"><h3>' + element["title"] + '</h3></a>' +
          '<p>' + element["summary"] + '</p>' +
          '<a class="btn ' + button_style + '" href="single-fund.html?id=' + element["id"] + '">Read More</a>'+
        '</div>'
        );
        
    });
    $('.company-gallery').slick('refresh');
  });