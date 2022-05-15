# Shef.AI


 <div align="center" width="50px"> 
     <a href="https://sheffieldai.github.io/"><img src="https://raw.githubusercontent.com/SheffieldAI/sheffieldai.github.io/main/images/favicon.png" alt="logo" width="20%" /></a>
     <p font-size="100px"><b>Sheffield Data Science and AI community</b></p> 
 </div>

----
![Website](https://img.shields.io/website?down_message=down&up_message=live&url=https%3A%2F%2Fsheffieldai.github.io%2F)
[![GitHub stars](https://img.shields.io/github/stars/SheffieldAI/sheffieldai.github.io)](https://github.com/SheffieldAI/sheffieldai.github.io/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/SheffieldAI/sheffieldai.github.io)](https://github.com/SheffieldAI/sheffieldai.github.io/network)
[![GitHub license](https://img.shields.io/github/license/SheffieldAI/sheffieldai.github.io)](https://github.com/SheffieldAI/sheffieldai.github.io/blob/main/LICENSE)

This is the official website for the Data Science and Artificial Intelligence community at The University of Sheffield. 

## How to update the LinkedIn post
To update the latest LinkedIn post on the website:
1. Navigate to the post on the [LinkedIn feed](https://www.linkedin.com/feed/) you want to embed to the [Shef.AI](https://sheffieldai.github.io/) website.
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
