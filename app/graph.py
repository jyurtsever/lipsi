import urllib.request
import re
import networkx as nx
import random
import multiprocessing
import json
from joblib import Parallel, delayed
from bs4 import BeautifulSoup
from rq import get_current_job
from app.wiki_objects import *

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

    convert_node = lambda node: {"group": node.group() % 50, "val": .5, "id": node.title()}
    convert_edge = lambda edge: {"source": edge[0].title(), "target": edge[1].title(), "value": .013}


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
    seen = {}
    seed_page = WikiPage(seed_link)
    Q = [seed_page]
    node_count, max_count = [0], 1500
    i, cuttoff = 0, 1000

    job = get_current_job()

    def explore(node):
        try:
            i = node_count[0]
            if i > max_count:
                return
            if job:
                job.meta['progress'] = 95.0 * i / max_count
                job.save_meta()

            items, titles_already_in_G = node.items(shuffle=True, seen=seen)
            for item in items:
                if item.title() not in seen:
                    node_count[0] += 1
                    new_Q.append(item)
                    G.add_edge(node, item)
                    seen[item.title()] = item

            for sl in titles_already_in_G:
                G.add_edge(seen[sl], node)

        except urllib.error.URLError:
            print(f'Error at {node.url()}')

    if job:
        print("ppewias: ", job.meta['progress'])

    while node_count[0] < max_count and i < cuttoff:
        new_Q = []
        Parallel(n_jobs=NUM_THREADS, require='sharedmem')(
            delayed(explore)(node) for node in Q)
        print(f"Current num pages: {node_count}")
        Q = new_Q
        i += 1
    print("finished while loop")
    if job:
        job.meta['progress'] = 100
        job.save_meta()
    return json.dumps(force_g_format(G))


def find_title(url):
    # webpage = urllib.request.urlopen(url).read()
    # title = str(webpage).split('<title>')[1].split('</title>')[0]
    # return title
    return url[len('http://en.wikipedia.org/wiki/'):]


def titlecase(s):
    return re.sub(r"[A-Za-z]+('[A-Za-z]+)?",
     lambda mo: mo.group(0)[0].upper() + mo.group(0)[1:].lower(), s)


