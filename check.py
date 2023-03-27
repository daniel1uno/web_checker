from langdetect import detect
from selenium import webdriver
from bs4 import BeautifulSoup
import requests
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import time
import random
from flask import Flask, render_template, request

options = webdriver.ChromeOptions()
options.add_argument('--headless') # Run Chrome in headless mode
driver = webdriver.Chrome(executable_path='chromedriver', options=options)

# Define an user agent to use in headers- mimic a browser
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
headers = {"User-Agent": user_agent}

app = Flask(__name__)
@app.route('/', methods=['GET', 'POST'])

def index():
    def check_web_page(urls):
        results = {}
        for url in urls:
            driver.get(url)
            for i in range(3): # scroll 20 times
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2) # wait for 2 seconds to load the next part of the page
            content = driver.page_source
            soup = BeautifulSoup(content, 'html.parser')
           
            correct_webpage = check_clone(url, soup)
            results[url + "_correct_webpage"] = correct_webpage
            if correct_webpage != True:
                continue

            lang_result = check_language(url,soup)
            results[url + "_language"] = lang_result
            img_result = check_images(url, soup)
            results[url + "_images"] = img_result
            js_result = check_js(url)
            results[url + "_js"] = js_result
            random_ref_result = check_ramdom_ref(url,soup)
            results[url + "_random_ref"] = random_ref_result
            
        
        driver.quit()
        return results

    def check_language(url,soup):
        try:
            content = " ".join([tag.text for tag in soup.find_all()])
            detected_lang = detect(content)
            if detected_lang == 'hi':
                print(url, "is in hindi")
                return True
            else:
                print(url, "is not in hindi")
                return False
        except:
            pass

    def check_images(url, soup):
        for img in soup.find_all(alt='Never stop learning.'):
            src = img.get("src")
            if src and "blur=" in src:
                print('Images in',url,'are blurred')
                return False
            
            else:
                print('Images in',url,'are good')
                return True

    #the threshold  was defined using a try-error approach
    def check_clone(url,soup):
        # Load the content of the original webpage
        given_content = requests.get('https://www.classcentral.com/').content
        soup2 = BeautifulSoup(given_content, 'html.parser')
        # Extract the textual content of the two webpages
        text1 = " ".join([tag.text for tag in soup.find_all()])
        text2 = " ".join([tag.text for tag in soup2.find_all()])
        
        # Compute the cosine similarity between the textual content of the two webpages
        vectorizer = CountVectorizer().fit_transform([text1, text2])
        similarity = cosine_similarity(vectorizer)[0,1]
        print(similarity)
        # Check if the similarity score is above a certain threshold
        if similarity >= 0.10:
            print(url, " and classcentral.com have the same content (its a clone of the correct page)")
            return True
        else:
            print(url, " and classcentral.com do not have the same content (its not a clone of the correct page)")
            return False

    def check_js(url):
        # Check for errors in the console output
        console_log = driver.get_log("browser")
        failed = []
        for entry in console_log:
            if entry["level"] == "SEVERE" and "Failed to load resource" in entry["message"] and ".js"  in entry["message"]:
                failed.append(False)
                print(url, " has unresolved js references, menus and hovers wont work")
        if False in failed:
            return False  
        else:
            return True

    def check_ramdom_ref(url,soup):
        # Find all href links on the page
        hrefs = [a.get("href") for a in soup.find_all("a")]
        # Select 5 random href links
        random_hrefs = random.sample(hrefs, 5)
        # Filter out any None values or empty strings
        random_hrefs = [href for href in random_hrefs if href]
        results_link = []
        for index, href in enumerate(random_hrefs):
            if href.startswith(('http://', 'https://')):
                pass
            else:
                random_hrefs[index] = url+href
                # Get webpage using request
                response = requests.get(url, headers=headers)
                soupLink = BeautifulSoup(response.content, "html.parser")
                result = check_language(href,soupLink)
                results_link.append(result)

        if False in results_link:
            return False
        else:
            return True

    if request.method == 'POST':
        # Retrieve the URLs entered by the user
        urls = request.form['urls'].split('\n')
        results = check_web_page(urls)
        print(results)
        return render_template('results.html', results=results)
    else:
        # Render the template with the form to enter URLs
        return render_template('index.html')
    
if __name__ == '__main__':
    app.run(debug=True)
