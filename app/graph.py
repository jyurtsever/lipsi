import urllib.request
import re
from bs4 import BeautifulSoup


def make_lst_from_seed(link):
    links = []
    with urllib.request.urlopen(link) as resp:
        soup = BeautifulSoup(resp, features="html.parser")
        for l in soup.find_all('a', href=re.compile("^(/wiki/)(.)*$")):
            links.append('http://en.wikipedia.org' + l['href'])
        return links

def make_graph_from_seed(link):

    pass