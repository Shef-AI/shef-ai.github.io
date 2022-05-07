fetch('../json/media-linkedin.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(function(element){
      $('#media-linkedin').append(
        '<iframe src="' + element["embed-link"] + '" height="500" width="90%" frameborder="0" allowfullscreen="" title="Embedded post">' +
        '</iframe>');
    });
  });