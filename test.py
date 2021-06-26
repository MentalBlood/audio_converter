import urllib3

http = urllib3.PoolManager()
data = http.request('GET', 'https://bandcamp.com/').data

from bs4 import BeautifulSoup
soup = BeautifulSoup(data, 'html.parser')