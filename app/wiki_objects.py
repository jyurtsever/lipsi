import urllib.request
import re
import random
import json
from bs4 import BeautifulSoup
from app.models import Wiki
from app import db
from urllib.parse import unquote



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