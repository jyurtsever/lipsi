import urllib.request
import re
import networkx as nx
import random
from bs4 import BeautifulSoup

random.seed(4)

def wiki_make_lst_from_seed(link):
    res = set()
    titles = {}
    with urllib.request.urlopen(link) as resp:
        soup = BeautifulSoup(resp, features="html.parser")
        for l in soup.find_all('a', href=re.compile("^(/wiki/)(.)*$")):
            if ':' not in l['href']:
                curr = 'http://en.wikipedia.org' + l['href']
                res.add(curr)
                titles[curr] = l['href'][len('/wiki/'):]
        return list(res), titles


def simple_force_g_format(G, titles):
    res = {}
    nodes = [{"id": node, "group": 1, "val": .5, "title": titles[node]} for node in G.nodes]
    links = [{"source": u, "target": v, "value": .01} for (u, v) in G.edges]
    res["nodes"], res["links"] = nodes, links
    return res


def force_g_format(G):
    res = {}
    nodes = [{"id": node.url(), "group": len(node.pages()), "val": .5, "title": node.title()} for node in G.nodes]
    links = [{"source": u.url(), "target": v.url(), "value": .01} for (u, v) in G.edges]
    res["nodes"], res["links"] = nodes, links
    return res

def simple_graph_from_seed(seed_link):
    links, titles = wiki_make_lst_from_seed(seed_link)
    titles[seed_link] = find_title(seed_link)
    links = links[:300]
    G = nx.Graph()
    G.add_node(seed_link)
    for link in links:
        G.add_node(link)
        G.add_edge(seed_link, link)
    return simple_force_g_format(G, titles)




def graph_from_seed(seed_link):
    G = nx.Graph()

    seen = set()
    seed_page = Page(seed_link)
    Q = [seed_page]
    category_lim, count = 50, 0
    while Q and count < category_lim:
        curr = Q.pop()
        print(curr, count)
        try:
            for item in curr.items(shuffle=False):
                if item.url() not in seen:
                    Q.append(item)
                    G.add_edge(curr, item)
                    seen.add(item.url())
            count += 1
        except urllib.error.URLError:
            print(f'Error at {curr.url()}')

    return force_g_format(G)


def find_title(url):
    # webpage = urllib.request.urlopen(url).read()
    # title = str(webpage).split('<title>')[1].split('</title>')[0]
    # return title
    return url[len('http://en.wikipedia.org/wiki/'):]



class Page:
    def __init__(self, url):
        self.url_ = url
        self.title_ = None
        self.sub_categories_ = None
        self.sup_categories_ = None
        self.home_ = 'http://en.wikipedia.org'

    def title(self):
        if not self.title_:
            # webpage = urllib.request.urlopen(url).read()
            # title = str(webpage).split('<title>')[1].split('</title>')[0]
            self.title_ = self.url_[len('http://en.wikipedia.org/wiki/'):]
        return self.title_

    def url(self):
        return self.url_

    def pages(self):
        return []

    def sub_categories(self):
        return []

    def sup_categories(self):
        if not self.sup_categories_:
            self.sup_categories_ = []
            with urllib.request.urlopen(self.url()) as resp:
                soup = BeautifulSoup(resp, 'html.parser')
                container = soup.find('div', id="mw-normal-catlinks")
                if container:
                    for atag in container.find_all('a'):
                        if atag['href'] != '/wiki/Help:Category':
                            self.sup_categories_.append(Category(self.home_ + atag['href']))
        return self.sup_categories_

    def items(self, shuffle=False):
        res = self.sup_categories() + self.pages() + self.sub_categories()
        return random.shuffle(res) if shuffle else res

    def __str__(self):
        return f'<<{self.url()}>>'


class Category(Page):
    def __init__(self, url):
        super().__init__(url)
        self.pages_ = None

    def sub_categories(self):
        if not self.sub_categories_:
            self.sub_categories_ = []
            self.sub_categories_ = []
            with urllib.request.urlopen(self.url()) as resp:
                soup = BeautifulSoup(resp, 'html.parser')
                container = soup.find('div', id="mw-subcategories")
                if container:
                    for atag in container.find_all('a'):
                        self.sub_categories_.append(Category(self.home_ + atag['href']))
        return self.sub_categories_

    def pages(self):
        if not self.pages_:
            self.pages_ = []
            with urllib.request.urlopen(self.url()) as resp:
                soup = BeautifulSoup(resp, 'html.parser')
                container = soup.find('div', id="mw-pages")
                if container:
                    for atag in container.find_all('a'):
                        if atag['title'] != 'Wikipedia:FAQ/Categorization':
                            self.pages_.append(Page(self.home_ + atag['href']))
        return self.pages_