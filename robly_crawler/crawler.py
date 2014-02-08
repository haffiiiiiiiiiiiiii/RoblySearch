import requests
from bs4 import BeautifulSoup
from robly_dto.website import Website
from robly_mongo.website_mongo import WebsiteMongo
from robly_parser import parser
import time
from tldextract import tldextract


def get_html(url):
    """
    Function to return the HTML content of a url
    """
    headers = {'Accept':'text/css,*/*;q=0.1',
        'Accept-Charset':'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding':'gzip,deflate,sdch',
        'Accept-Language':'en-US,en;q=0.8',
        'User-Agent':'Mozilla/5 (Windows 7) Gecko'}
    res = requests.get(url, headers=headers)
    return str(BeautifulSoup(res.content))


def get_base_url(url):
    """
    Takes as input a url, returns the protocol,domain and suffix concatenated
    to form the base url of the website. Uses the tldextract library.
    """
    tld = tldextract.extract(url)
    print(tld.subdomain, ' - ', tld.domain, ' - ', tld.suffix)
    if tld.subdomain != "":
        base_url = '.'.join([tld.subdomain, tld.domain, tld.suffix])
    else:
        base_url = '.'.join([tld.domain, tld.suffix])
    return base_url

def get_protocol(url):
    """
    Returns whether the url is https or http and returns the protocol as a string
    """
    if url.startswith('https'):
        protocol = "https://"
    else:
        protocol = "http://"
    return protocol


def merge_link_with_base_url(url, link):
    """
    Function that gets the base url of the passed url, and merges it with the
    passed link and returns the concatenated string.
    e.g. When url = 'http://roblynch.info/awesome/stuff'
    and link = '/static/images/logo.png'
    The resulting merged string will look like "http://roblynch.info/static/image/logo.png"
    Params:     url - a string containing the url to be merged with the link
                link - the string link to be appended to the base_url.
                       Only links beginning with '/' are accepted
    Returns:    A merged string containing:
                The protocol of the url, the merged base url and the link
    """
    #Get protocol
    protocol = get_protocol(url)
    #Get base url
    base_url = get_base_url(url)
    #Join protocol to base url to link
    if link.startswith('/'):
        merged_string = protocol + base_url + link
    else:
            merged_string = protocol + base_url + '/' + link
    return merged_string


def insert_websites_to_mongo(website_list):
    """
    Function to insert a list of website objects into mongodb
    """
    mongo = WebsiteMongo()
    for w in website_list:
        print("Inserting", w.url, "into mongodb")
        mongo.create_website(w)


def crawl_website_insert_to_database(url):
    """
    Function to crawl the given url and the pages it links to at a depth of 1.
    Params:     string - the url of the website that is to be crawled
    Returns:    List - of website objects containing each of the crawled websites data
    """
    website = get_website_object(url)
    print("Number of website that will be crawled =", len(website.links))
    if website:
        website_list = [website]
        if website.links:
            for w in website.links:
                #Append base url to beginning of links beginning with /
                if w.startswith('/'):
                    w = merge_link_with_base_url(website.url, w)
                #Crawl the valid links
                if w != url and not '#' in w and not w.startswith('/') and w.startswith('http'):
                    website_obj = get_website_object(w)
                    website_list.append(website_obj)
                time.sleep(2)
        insert_websites_to_mongo(website_list)

def insert_base_url_before_relative_path_links(url, images):
    for n, image in enumerate(images):
        if not image.startswith('http'):
            #Append base url to the image link
            images[n] = merge_link_with_base_url(url, image)
    return images



def get_website_object(url):
    """
    This function parses the url, creates a website object for easy access
    to all html elements that are to be stored in the database.
    Params : url        The url of the website to be parsed
    Return : website    Website object containing all websites data
    """
    print("crawling - ", url)
    #get html
    try:
        html = get_html(url)
    except Exception:
        pass
    #parse website info
    try:
        soup = BeautifulSoup(html)
    except Exception:
        pass

    if soup:
        #title
        try:
            title = get_title(soup)
        except Exception:
            title = ""
        #description
        try:
            description = get_description(soup)
        except Exception:
            description = ""
        #keyword list
        try:
            keywords = get_keywords(soup)
            keywords = list(set(keywords))
        except Exception:
            keywords = []
        #robots follow
        try:
            robots_index = robots_should_index(soup)
        except Exception:
            robots_index = True
        #links
        try:
            links = get_links(soup)
            #Remove duplicates from list of links
            links = list(set(links))
        except Exception:
            links = []
        #h1s
        try:
            h1s = get_h1s(soup)
            h1s = list(set(h1s))
        except Exception:
            h1s = []
        #images
        try:
            images = get_images(soup)
            #remove duplicates from images
            images = list(set(images))
            #make sure each image is a full url
            images = insert_base_url_before_relative_path_links(url, images)
        except Exception:
            images = []
        ## Get the text of the web page
        try:
            non_html = soup.get_text()
            non_html = parser.prune_string(non_html)
        except Exception:
            non_html = ""

        #Create website object
        website = Website(url, title, h1s, links, images, non_html, description,
                          keywords, robots_index)
        return website
    else:
        return None


def get_title(soup):
    """
    Returns the title of the web page
    """
    return soup.title.string


def get_images(soup):
    """
    Returns: A list of URL for images found on the page
    """
    images = []
    for pic in soup.find_all('img'):
        images.append(pic.get('src'))
    return images


def get_links(soup):
    """
    Returns:    A list of url links found on the page.
    """
    links = []
    for link in soup.find_all('a'):
        links.append(link.get('href'))
    return links


def get_h1s(soup):
    """
    Returns:    A list of header 1 tags found on the web page
    """
    h1s = []
    for h1 in soup.find_all('h1'):
        h1s.append(h1.string)
    return h1s


def get_keywords(soup):
    """
    Returns:    A list of keywords found in the meta tags of the webpage
    """
    keyword_string = soup.find("meta", {"name": "keywords"})['content']
    return keyword_string.split(',')


def get_description(soup):
    """
    Returns:    A string description of the website found in the meta tags in the website
    """
    return soup.find("meta", {"name": "description"})['content']


def robots_should_index(soup):
    """
    Returns:    True if the web page wants to be indexed
                False if the web page does not want to be indexed
    """
    if "noindex" in soup.find("meta", {"name": "robots"})['content']:
        return False
    else:
        return True