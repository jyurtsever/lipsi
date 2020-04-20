import urllib.request
import re
import random
import json
import wikipedia
import requests
from bs4 import BeautifulSoup
from app.models import Wiki
from app import db
from urllib.parse import unquote


random.seed(4)

class Page:
    def title(self):
        raise NotImplementedError()

    def url(self):
        raise NotImplementedError()

    def items(self, shuffle=False, seen=None):
        raise NotImplementedError()

    def images(self):
        raise NotImplementedError()

    def group(self):
        raise NotImplementedError

    def __str__(self):
        return f'<<{self.url()}>>'

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash(self.title())


class WikiPage(Page):
    """Uses Only Wikipedia php API"""
    def __init__(self, title, link_lim=15):
        self.title_ = title
        self.items_ = []
        self.images_ = None
        self.summary_ = None
        self.home_ = "https://en.wikipedia.org/wiki/"
        self.length_ = None
        self.url_ = self.home_ + self.title_
        self.link_lim = link_lim
        self.seen_link_lim = link_lim
        self.group_ = 3


    def title(self):
        return self.title_

    def url(self):
        return self.url_

    def is_valid(self, title):
        return ':' not in title

    def __len__(self):
        if not self.length_:
            self.length_ = self.query_api('info', self.title())["length"]
        return self.length_

    def images(self):
        if not self.images_:
            self.images_ = self.query_api('images', self.title())
        return self.images_


    def items(self, shuffle=False, seen=None):
        """
        :param shuffle: whether to shuffle the result or not
        :param seen: the seen titles of the graph
        :return:
        """
        if not self.items_:
            titles = self.query_api('links', self.title())
            if not titles:
                return [], []

            if shuffle:
                random.shuffle(titles)
            seen_links, res = [], []
            num_links, num_seen_links = 0, 0

            for t in titles:
                if t in seen and num_seen_links < self.seen_link_lim:
                    seen_links.append(t)
                    num_seen_links += 1
                elif self.is_valid(t) and num_links < self.link_lim:
                    res.append(WikiPage(t))
                    num_links += 1
                if num_links > self.link_lim and num_seen_links > self.seen_link_lim:
                    break
            self.items_ = (res, seen_links)
            self.group_ = len(titles)
        return self.items_

    def group(self):
        return self.group_

    @staticmethod
    def prefix_search(semi_title):
        query = WikiPage.query_api('prefixsearch', semi_title,
                                   query_param='list', target='prefixsearch', title_key='pssearch')
        return [q['title'] for q in query]

    @staticmethod
    def query_api(prop, title, query_param='prop', target='pages', title_key='titles'):
        """
        :param prop: property being queried
        :param title:
        :return:
        """
        session = requests.Session()
        url = "https://en.wikipedia.org/w/api.php"

        continue_keys = {"images": "imcontinue", "links": "plcontinue", "linkshere": "lhcontinue"}
        lim_keys = {"images": "imlimit", "links": "pllimit", "linkshere": "lhlimit"}

        params = {
            "action": "query",
            "format": "json",
            title_key: title,
            query_param: prop,
        }

        if prop in ('images', 'links', 'linkshere'):
            params[lim_keys[prop]] = 'max'


        response = session.get(url=url, params=params)
        data = response.json()
        pages = data["query"][target]
        try:
            if prop in ('links', 'images', 'linkshere'):
                pg_count = 1
                titles = []
                while pg_count < 5:
                    # print("\nPage %d" % pg_count)
                    for key, val in pages.items():
                        for link in val[prop]:
                            titles.append(link["title"])

                    if "continue" not in data:
                        break

                    continue_key = continue_keys[prop]
                    continue_val = data["continue"][continue_key]
                    params[continue_key] = continue_val
                    response = session.get(url=url, params=params)
                    data = response.json()
                    pages = data["query"][target]
                    pg_count += 1

                # print("%d titles found." % len(titles))
                return titles

            elif prop == 'info':
                k = list(pages.keys())[0]
                return pages[k]

            elif prop == 'prefixsearch':
                return pages
            else:
                raise AssertionError("Property not Recognized")
        except KeyError as kE:
            print(f'Unable to find property "{kE}" for page titled "{title}"')
            print(data)




class PyWikiPage(Page):
    """Uses Wikipedia Python Api"""
    def __init__(self, title, link_lim=10):
        self.wiki_ = wikipedia.page(title)
        self.title_ = title
        self.items_ = None
        self.images_ = None
        self.summary_ = None
        self.url_ = None
        self.link_lim =  link_lim

    def title(self):
        return self.title_

    def url(self):
        if not self.url_:
            self.url_ = self.wiki_.url
        return self.url_

    def images(self):
        if not self.url_:
            self.images_ = self.wiki_.images
        return self.images_

    def items(self, shuffle=False, seen=None):
        if not self.items_:
            links = self.wiki_.links
            random.shuffle(links)
            if len(links) > self.link_lim:
                return links
            return links
    @staticmethod
    def validate_link(link):
        return ':' not in link





class ScrapePage(Page):
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
            self.sup_categories_ = [ScrapeCategory(u) for u in url_query]


        return self.sup_categories_

    def items(self, shuffle=False, seen=None):

        query = Wiki.query.filter_by(id=self.url()).first()
        if query:
            print('using database')
            children_dict = json.loads(query.children)
            self.sup_categories_ = [ScrapeCategory(u) for u in children_dict['sup_cat_links']]
            self.pages_ = [ScrapePage(u) for u in children_dict['page_links']]
            self.sub_categories_ = [ScrapeCategory(u) for u in children_dict['sub_cat_links']]
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
        return res, []

    def images(self):
        return []




class ScrapeCategory(ScrapePage):
    def sub_categories(self):
        """
        :return: List of Category objects corresponding to subcategories
        """

        if not self.sub_categories_:
            self.sub_categories_ = [ScrapeCategory(u) for u in
                                     self.links_in_div("mw-subcategories", self.is_valid_category)]
        return self.sub_categories_

    def pages(self):
        """
        :return: List of page objects corresponding to pages in a category
        """
        if not self.pages_:
            self.pages_ = [ScrapePage(u) for u in
                            self.links_in_div("mw-pages", self.is_valid_category)]
        return self.pages_