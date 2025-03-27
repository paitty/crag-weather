import requests
from bs4 import BeautifulSoup

headers = {'Accept':	'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding':	'gzip, deflate, br, zstd',
    'Accept-Language':	'en-US,fr;q=0.8,hr;q=0.5,en;q=0.3',
    'Connection':	'keep-alive',
    'DNT':	'1',
    'Priority':	'u=0, i',
    'Sec-Fetch-Dest':	'document',
    'Sec-Fetch-Mode':	'navigate',
    'Sec-Fetch-Site':	'none',
    'Sec-Fetch-User':	'?1',
    'Sec-GPC':	'1',
    'sitename': 'https://github.com/paitty/crag-weather.git',
    'Upgrade-Insecure-Requests':	'1',
    'User-Agent':	'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0'}

url = "https://www.plivazdravlje.hr/alergije/prognoza/1/zagreb.html"
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.content,"html.parser")

for soup3 in soup.find_all('div'):
    #print(soup3.get("class"))
    if soup3.get("class"):
        if soup3.get("class")[0] == "peludHolder":
            for soup2 in soup3.find_all('div'):
                if soup2.get("class")[0] == "peludKategorija":
                    break
            for soup1 in soup3.find_all('span'):
                if soup1.get("class"):
                    if soup1.get("class")[0] == "peludStupacOcitanje":
                        break
            print(soup2.text.strip()+": "+soup1.text.strip())


pass