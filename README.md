# Shef.AI


 <div align="center" width="50px"> 
     <a href="https://shef-ai.github.io/"><img src="https://avatars.githubusercontent.com/u/94853016?s=400&u=4c39d19e8e83f556b8d0c13170df35178ff669f0&v=4" alt="logo" width="20%" /></a>
     <p font-size="100px"><b>Sheffield Data Science and AI Community</b></p> 
 </div>

----
![Website](https://img.shields.io/website?down_message=down&up_message=live&url=https%3A%2F%2Fshef-ai.github.io%2F)
[![GitHub stars](https://img.shields.io/github/stars/shef-ai/shef-ai.github.io)](https://github.com/shef-ai/shef-ai.github.io/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/shef-ai/shef-ai.github.io)](https://github.com/shef-ai/shef-ai.github.io/network)
[![GitHub license](https://img.shields.io/github/license/shef-ai/shef-ai.github.io)](https://github.com/shef-ai/shef-ai.github.io/blob/main/LICENSE)

This is the official website for the Sheffield Data Science and AI Community. 

## How to update the LinkedIn post
To update the latest LinkedIn post on the website:
1. Navigate to the post on the [LinkedIn feed](https://www.linkedin.com/feed/) you want to embed to the [Shef.AI](https://shef-ai.github.io/) website.
3. Click the **More** icon in the post’s top right corner.
4. Click **Embed this post**.
5. Copy the url that is available in `scr` attribute from the pop-up window.
   - Let’s consider the following pop-up is shown when you clicked on **Embed this post**:
     ```
     <iframe src="https://www.linkedin.com/embed/feed/update/urn:li:share:6922167380462698496" 
     height="834" width="504" frameborder="0" allowfullscreen="" title="Embedded post"></iframe>
     ```
   - From the above code, only copy the url in the `scr` attribute, i.e.,
     ```
     https://www.linkedin.com/embed/feed/update/urn:li:share:6922167380462698496
     ```
7.	Open the `media-linkedin.json` file that is available in `json` folder of the project repository.
8.	Replace the url in `embed-link` field with the copied link from LinkedIn.


## How to update news/events content
All news/events data have been stored in the `.json` files available in the `json` folder of the project repository.
Provided below are the steps you can pass to update the news/events data:
1. Prepare the text you are going to put on the website. If you are willing to use the formatted text, you can use one of the following converter websites to generate HTML code from your rich text:
   - https://onlinehtmleditor.dev/
   - https://wordtohtml.net/
   
   Please write your text in the text box and convert it to HTML codes.
2. When your text has been formatted and HTML code has been generated, you must convert it to a single-line JSON file. In other words, multiline texts are not allowed to be used in JSON files. You can convert a multiline formatted text to a single-line text using the following website:
   - https://tools.knowledgewalls.com/online-multiline-to-single-line-converter
3. You have now prepared your text in JSON format. The last step is to update a record in the `.json` files:
   1. Open the `news.json` or `events.json` file in the `json` folder of the project repository.
   2. Replace the value of your desired field with the generated single-line text from the previous steps.
   
## Privacy notice
To see our Privacy Notice, please go to [Shef.AI Website Policy Notice](https://shef-ai.github.io/privacy-notice.html) about what types of personal information will be gathered and how this information will be used.

