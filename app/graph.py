import urllib.request
import re
import networkx as nx
import random
import multiprocessing
import json
import time
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



def force_g_format(G):
    """
    :param G: nx Graph of articles to display
    :return: json format to send to javascript to render the graph u
    """
    res = {}
    print("started force G formatting")
    print("node length: ", len(G.nodes))
    print("edge length: ", len(G.edges))

    convert_node = lambda node: {"color": node.color(), "val": .5, "id": node.id(), "pageimage": node.pageimage(), "title": node.title()}
    convert_edge = lambda edge: {"source": edge[0].id(), "target": edge[1].id(), "value": 10000}


    nodes = Parallel(n_jobs=NUM_THREADS, prefer="threads")(delayed(convert_node)(node) for node in G.nodes)
    links = Parallel(n_jobs=NUM_THREADS, prefer="threads")(delayed(convert_edge)(edge) for edge in G.edges)
    res["nodes"], res["links"] = nodes, links
    return res





def graph_from_seed(seed_title, start_id=0, seed_id=0, max_count=850):
    """
    :param seed_title: title to start the graphing process
    :return: nx Graph object, the resulting graph of exploration
    """
    print(seed_title)
    # Start time
    start_time = time.time()

    G = nx.Graph()
    seed_page = WikiPage(seed_title)
    seen = {seed_page.title(): seed_page}

    Q = [seed_page]
    G.add_node(seed_page)

    # Hard coded thresholds and cutoffs!
    node_count = [0]
    i, cuttoff = 0, 650
    seen_to_num_nodes_thresh = 0.08
    max_links, max_seen_links = 15, 20
    time_cutoff = 80*1e3 #one minute

    job = get_current_job()

    def explore(node):
        try:
            i = node_count[0]
            time_elapsed = time.time() - start_time
            if i > max_count or time_elapsed > time_cutoff:
                return
            if job:
                job.meta['progress'] = 95.0 * max(i / max_count, time_elapsed / time_cutoff)
                job.save_meta()

            items, titles_already_in_G = node.items(shuffle=True, seen=seen)

            # check if we are greater than threshold
            num_nodes = G.number_of_nodes()


            if num_nodes == 1 or len(titles_already_in_G)/num_nodes > seen_to_num_nodes_thresh:

                for j, item in enumerate(items):
                    if j > max_links:
                        break
                    if item.title() not in seen:
                        node_count[0] += 1
                        new_Q.append(item)
                        G.add_edge(node, item)
                        seen[item.title()] = item

                for j, sl in enumerate(titles_already_in_G):
                    if j > max_seen_links:
                        break
                    G.add_edge(seen[sl], node)

        except urllib.error.URLError:
            print(f'Error at {node.url()}')

    while node_count[0] < max_count and i < cuttoff:
        new_Q = []

        #Cut off if taking too long
        if time.time() - start_time > time_cutoff:
            break

        Parallel(n_jobs=NUM_THREADS, require='sharedmem')(
            delayed(explore)(node) for node in Q)
        Q = new_Q
        i += 1
    print("finished while loop")
    if job:
        job.meta['progress'] = 100
        job.save_meta()

    # Adding integer ID to each node
    for i, node in enumerate(G.nodes):
        if i == 0:
            node.set_id(seed_id)
            # if seed_id != 0:
            #     node.set_edge_val(100)
        else:
            node.set_id(i + start_id)
    return json.dumps(force_g_format(G))



