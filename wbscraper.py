import requests
from bs4 import BeautifulSoup
import re

from urllib.request import urlopen
from urllib.request import Request
from urllib.parse import urlparse

from selenium import webdriver 
from selenium.webdriver.chrome.service import Service as ChromeService 
from webdriver_manager.chrome import ChromeDriverManager 
from selenium.webdriver.common.by import By

import time
import pandas as pd


#Your google search, for example I wanted to search nesquik chocolate milk (I have no idea why O.o)
SEARCH_STRING = 'nesquik chocolate milk'

#keywords that you want included for sure inside of your results (for example, each result must contain the following three words
FILTER_PHRASES = ['nesquik', 'chocolate', 'milk']

#number of starting websites to scrape, usually 15 is more than enough...but as mentioned before, my search imagination is quite limited so who knows
NUM_ENTRIES = 15

#advanced parameter, prevents website from banning ip due to botnet DDOS
SLEEP_TIME = 20

#Selenium Browser wait time | allows for the webpage to fully load before scraping
WAIT_TIME = 50





class WebPath:
    def __init__(self, path):
        self.path = path

    def set_rule(self):
        asterisk_re_rule = r"[\w/]*"
        
        self.path_pattern = re.compile(self.path.replace('*', asterisk_re_rule))
        
    def check_match(self, s):
        result_first = self.path_pattern.match(s)
        
        if result_first == None or not(result_first.group() == s):
            return False

        return True


class Robot:
    def __init__(self):
        self.allowfile = []
        self.disallowfile = []
        self.urlfile = None

    def setfile(self, url):

        response = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Chrome'}))
        soup = BeautifulSoup(response, 'html.parser', from_encoding=response.info().get_param('charset'))

        file = str(soup).splitlines()
        
        startindex = file.index('User-agent: *')
        endindex = startindex+1

        while 'Allow' in file[endindex] or 'Disallow' in file[endindex]:
            endindex += 1

        #.robotfile = file[startindex:endindex]

        for x in file[startindex+1:endindex]:
            if 'Allow' in x.split(' ')[0]:
                self.allowfile.append(x.split(' ')[1])
            else:
                self.disallowfile.append(x.split(' ')[1])

    def checkpath(self, val):
        pathindex = val[10:].index('/')
        path = val[pathindex+10:]

        print(path)
        
        for x in self.allowfile:
            q = WebPath(x)
            q.set_rule()
            r = q.check_match(path)

            if r:
                return True
            
        for x in self.disallowfile:
            q = WebPath(x)
            q.set_rule()
            r = q.check_match(path)

            if r:
                return False
            
        return True


class VMBrowser:
    def __init__(self, headless):

        options = webdriver.ChromeOptions() 
        options.headless = headless
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options) 

    def setUrl(self, url):
        self.url = url

    def getWebPage(self):
        self.driver.get(self.url)

        time.sleep(SLEEP_TIME)
        
        self.driver.implicitly_wait(WAIT_TIME)

        content = self.driver.page_source
        return BeautifulSoup(content, 'html.parser')

    

class Item:
    def __init__(self, url, nodetect=False):
        d = VMBrowser(headless=True)

        d.setUrl(url)

        self.object = d.getWebPage()
        self.price, self.name, self.attrs = None, None, {}

class AmazonItem(Item):
    def __init__(self, url):
        super().__init__(url)

    def getPrice(self, returnVal=False):
        price_dollar_tag = str(self.object.find('span', class_="a-price-whole"))
        
        tag_index_start = price_dollar_tag.index('>')
        tag_index_end = price_dollar_tag[1:].index('<')
        
        price_dollar = price_dollar_tag[tag_index_start+1:tag_index_end+1]
        

        price_cents_tag = str(self.object.find('span', class_="a-price-fraction"))

        tag_index_start = price_cents_tag.index('>')
        tag_index_end = price_cents_tag[1:].index('<')

        price_cents = price_cents_tag[tag_index_start+1:tag_index_end+1]

        self.price = float(price_dollar+'.'+price_cents)

        if returnVal:
            return self.price

    def getName(self, returnVal=False):
       name_tag = str(self.object.find('span', class_="a-size-large product-title-word-break"))
       #print(self.object.find('span', class_="a-size-large product-title-word-break"))

       tag_index_start = name_tag.index('>')
       tag_index_end = name_tag[1:].index('<')

       name_unfiltered = name_tag[tag_index_start+1:tag_index_end+1]

       self.name = name_unfiltered.strip()

       if returnVal:
           return self.name

    def getAttributes(self, returnVal=False):
        obj = self.object.find('table', id='productDetails_detailBullets_sections1') # its one - 1

        if(obj == None):
            print("Other Choice")
            obj = self.object.find('table', id='productDetails_detailBullets_sectionsl') # its the letter ell - l
            
        for row in obj.findAll('tr'):
            aux_head = row.find('th')

            if aux_head.string == 'Customer Reviews':
                aux_val = row.find(string=re.compile(r"[\s\S]*out of[\s\S]*"))

            #ignored Best Sellers Rank for now - not enough evidence to create a general scaper
            elif aux_head.string == ' Best Sellers Rank ':
                continue

            elif aux_head.string == ' International Shipping ':
                aux_val = row.find(string=re.compile(r"[\s\S]*"))
                
            else:
                aux_val = row.find('td')

            self.attrs[aux_head.string] = aux_val.string

        if returnVal:
           return self.attrs

class AmazonPage(Item):
    def __init__(self, url):
        super().__init__(url)
        self.pages = None

    def extractURLS(self, returnVal=False):
        self.pages = self.object.find_all(class_ = "a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal")
        
        self.pages = set(['https://amazon.com'+link.get('href') for link in self.pages])

        if returnVal:
           return self.pages
        
    @staticmethod
    def scrape(url):
        a = AmazonItem(url)
        return {'name' : a.getName(returnVal=True), 'price' : a.getPrice(returnVal=True), 'url' : url}#, 'attributes' : a.getAttributes()})

    @staticmethod
    def crawl(returnVal = True, urls=[]):
        k, ind=[], 0
        for url in urls:
            try:
                k.append(AmazonPage.scrape(url))
                time.sleep(2)
                print('--------------------------------------')
                print('Site# ::  ', ind)
                print(k[ind])
                print('--------------------------------------')
                ind += 1
            except:
                print('--------------------------------------')
                print('Incompatible Webpage -----------')
                print(url)
                print('--------------------------------------')
        if returnVal:
            return k

#a = AmazonPage('')
#a.extractURLS(returnVal=True)
#a.crawl()

#a=AmazonItem('https://www.amazon.com/NESQUIK-Ready-Drink-Chocolate-Count/dp/B07P6TDXV1')
#print(a.object)
#print(a.getPrice(returnVal=True))



try:
    from googlesearch import search
except ImportError:
    print("No module named 'google' found")
 
# to search
#query = "nesquik chocolate milk amazon"
query = SEARCH_STRING + " amazon"

urls = [str(j) for j in search(query, num=NUM_ENTRIES, stop=NUM_ENTRIES, pause=5)]

pattern = re.compile(r"https://www.amazon.com/[\s\S]*")

def reMatch(pattern, url):
    if pattern.match(url) is None or not(pattern.match(url).group() == url):
        return False
    return True

solidUrls = []
productUrls, catalogUrls = set(), set()
for x in urls:
    if reMatch(pattern, x):
        solidUrls.append(x)

productPattern = re.compile(r"https://www.amazon.com/[\S]*/dp/[\S]*")
catalogPattern = re.compile(r"https://www.amazon.com/[\S]*/s\?k=[\S]*")

for x in urls:
    if reMatch(pattern, x):
        solidUrls.append(x)


for x in solidUrls:
    if reMatch(productPattern,x):
        productUrls.add(x)
    elif reMatch(catalogPattern, x):
        catalogUrls.add(x)
    else:
        continue


for x in catalogUrls:
    a = AmazonPage(x)
    productUrls = productUrls.union(a.extractURLS(returnVal=True))
    


results = AmazonPage.crawl(urls=productUrls)

df = pd.DataFrame(results)



catchPhrases, delist = FILTER_PHRASES, []

for x in range(len(df)):
  name, value = df.iat[x,0], df.iat[x,1]

  for y in catchPhrases:
    if not(y in name.lower()):
      delist.append(x)
      break
  
    
df.drop(labels=delist, axis=0, inplace=True)

df.sort_values(axis=0, ascending=False, inplace=True, by=['price'])


df.to_csv('results.csv', encoding='utf-8')

