import urllib.request
import re
import networkx as nx
import random
import multiprocessing
import json
from tqdm import tqdm
from joblib import Parallel, delayed
from bs4 import BeautifulSoup
from app.models import Wiki
from app import db
from itertools import chain, count
from urllib.parse import unquote


random.seed(4)
NUM_THREADS = multiprocessing.cpu_count()


def wiki_make_lst_from_seed(link):
    """
    :param link: string
    :return: List of urls to display and titles
    """
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
    print("node length: ", len(G.nodes))
    nodes = [{"id": node, "group": 1, "val": .5, "title": titles[node]} for node in G.nodes]
    links = [{"source": u, "target": v, "value": .01} for (u, v) in G.edges]
    res["nodes"], res["links"] = nodes, links
    return res


def force_g_format(G):
    """
    :param G: nx Graph of articles to display
    :return: json format to send to javascript to render the graph u
    """
    res = {}
    print("started force G formatting")
    print("node length: ", len(G.nodes))
    print("edge length: ", len(G.edges))

    convert_node = lambda node: {"id": node.url(), "group": len(node.pages_), "val": .5, "title": node.title()}
    convert_edge = lambda edge: {"source": edge[0].url(), "target": edge[1].url(), "value": .01}

    # print([dict(chain(G.nodes[n].items(), [(name, n)])) for n in G])
    nodes = Parallel(n_jobs=NUM_THREADS, prefer="threads")(delayed(convert_node)(node) for node in G.nodes)
    links = Parallel(n_jobs=NUM_THREADS, prefer="threads")(delayed(convert_edge)(edge) for edge in G.edges)
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
    """
    :param seed_link: url to start the graphing proces
    :return: nx Graph object, the resulting graph of exploration
    """
    print(seed_link)
    G = nx.Graph()
    seen = set()
    seed_page = Page(seed_link)
    Q = [seed_page]
    count, max_count = [0], 30
    i, cuttoff = 0, 1000

    def explore(node):
        try:
            if count[0] > max_count:
                return
            count[0] += 1
            if count[0] % 100 == 0:
                print(node)
                print(f"Current num pages: {count[0]}")
            for item in node.items(shuffle=True):
                if item.url() not in seen:
                    new_Q.append(item)
                    G.add_edge(node, item)
                    seen.add(item.url())
        except urllib.error.URLError:
            print(f'Error at {node.url()}')

    while count[0] < max_count and i < cuttoff:
        new_Q = []
        Parallel(n_jobs=NUM_THREADS, require='sharedmem')(
            delayed(explore)(node) for node in Q)
        print(f"Current num pages: {count}")
        Q = new_Q
        i += 1
    print("finished while loop")
    return force_g_format(G)


def find_title(url):
    # webpage = urllib.request.urlopen(url).read()
    # title = str(webpage).split('<title>')[1].split('</title>')[0]
    # return title
    return url[len('http://en.wikipedia.org/wiki/'):]


def titlecase(s):
    return re.sub(r"[A-Za-z]+('[A-Za-z]+)?",
     lambda mo: mo.group(0)[0].upper() + mo.group(0)[1:].lower(), s)


class Page:
    def __init__(self, url):
        self.url_ = url
        self.title_ = None
        self.sub_categories_ = None
        self.sup_categories_ = None
        self.pages_ = []
        self.home_ = 'http://en.wikipedia.org'

    def title(self):
        """
        :return: title as a string
        """
        if not self.title_:
            # webpage = urllib.request.urlopen(url).read()
            # title = str(webpage).split('<title>')[1].split('</title>')[0]
            self.title_ = unquote(self.url_)[len('http://en.wikipedia.org/wiki/'):].replace('_', ' ')
        return self.title_

    def url(self):
        """
        :return: url as a string
        """
        return self.url_

    def pages(self):
        return self.pages_

    def sub_categories(self):
        return []

    def is_valid_category(self, s):
        return (s != '/wiki/Help:Category' and 'Wikipedia' not in s
               and not bool(re.match(r'.*\d{4}.*', s)))

    def is_valid_page(self, s):
        return s != 'Wikipedia:FAQ/Categorization'

    def links_in_div(self, div_id, validator_fn):
        """
        :param div_id: id of html div to scrape
        :param validator_fn: function to check if url should be appended (for example is_valid_page)
        :return: list of urls
        """
        res = []
        with urllib.request.urlopen(self.url()) as resp:
            soup = BeautifulSoup(resp, 'html.parser')
            container = soup.find('div', id=div_id)
            if container:
                for atag in container.find_all('a'):
                    if validator_fn(atag['href']):
                        res.append(self.home_ + atag['href'])
        return res
    def sup_categories(self):
        """
        :return: List of Category objects corresponding to super-categories (i, e the category the object is in
        """

        if not self.sup_categories_:
            url_query = self.links_in_div("mw-normal-catlinks", self.is_valid_category)
            self.sup_categories_ = [Category(u) for u in url_query]


        return self.sup_categories_

    def items(self, shuffle=False):

        query = Wiki.query.filter_by(id=self.url()).first()
        if query:
            print('using database')
            children_dict = json.loads(query.children)
            self.sup_categories_ = [Category(u) for u in children_dict['sup_cat_links']]
            self.pages_ = [Page(u) for u in children_dict['page_links']]
            self.sub_categories_ = [Category(u) for u in children_dict['sub_cat_links']]
        else:
            sub_cat_links = [c.url() for c in self.sub_categories()]
            sup_cat_links = [c.url() for c in self.sup_categories()]
            page_links = [p.url() for p in self.pages()]

            children_dict = {'sup_cat_links': sup_cat_links, 'page_links': page_links, 'sub_cat_links': sub_cat_links}
            wiki = Wiki(id=self.url(), children=json.dumps(children_dict), image_urls=json.dumps([]))

            db.session.add(wiki)
            db.session.commit()

        res = self.sup_categories() + self.pages() + self.sub_categories()

        if shuffle:
            random.shuffle(res)
        return res

    def __str__(self):
        return f'<<{self.url()}>>'


class Category(Page):
    def sub_categories(self):
        """
        :return: List of Category objects corresponding to subcategories
        """

        if not self.sub_categories_:
            self.sub_categories_ = [Category(u) for u in
                                     self.links_in_div("mw-subcategories", self.is_valid_category)]
        return self.sub_categories_

    def pages(self):
        """
        :return: List of page objects corresponding to pages in a category
        """
        if not self.pages_:
            self.pages_ = [Page(u) for u in
                            self.links_in_div("mw-pages", self.is_valid_category)]
        return self.pages_