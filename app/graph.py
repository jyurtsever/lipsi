import urllib.request
import re
import networkx as nx
from bs4 import BeautifulSoup


def make_lst_from_seed(link):
    links = set()
    with urllib.request.urlopen(link) as resp:
        soup = BeautifulSoup(resp, features="html.parser")
        for l in soup.find_all('a', href=re.compile("^(/wiki/)(.)*$")):
            links.add('http://en.wikipedia.org' + l['href'])
        return list(links)


def force_g_format(G):
    res = {}
    nodes = [{"id": node, "group": 1, "val": .5} for node in G.nodes]
    links = [{"source": u, "target": v, "value": .01 } for (u, v) in G.edges]
    res["nodes"], res["links"] = nodes, links
    return res


def make_graph_from_seed(seed_link):
    links = make_lst_from_seed(seed_link)[:15]
    G = nx.Graph()
    G.add_node(seed_link)
    for link in links:
        G.add_node(link)
        G.add_edge(seed_link, link)
    return force_g_format(G)
