import urllib.request
import re
import networkx as nx
from bs4 import BeautifulSoup


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


def force_g_format(G, titles):
    res = {}
    nodes = [{"id": node, "group": 1, "val": .5, "title": titles[node]} for node in G.nodes]
    links = [{"source": u, "target": v, "value": .01 } for (u, v) in G.edges]
    res["nodes"], res["links"] = nodes, links
    return res


def make_graph_from_seed(seed_link):
    links, titles = wiki_make_lst_from_seed(seed_link)
    titles[seed_link] = find_title(seed_link)
    links = links[:300]
    G = nx.Graph()
    G.add_node(seed_link)
    for link in links:
        G.add_node(link)
        G.add_edge(seed_link, link)
    return force_g_format(G, titles)


def find_title(url):
    webpage = urllib.request.urlopen(url).read()
    title = str(webpage).split('<title>')[1].split('</title>')[0]
    return title