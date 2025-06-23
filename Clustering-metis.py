import etcd3
import json
import networkx as nx
import metis
from collections import defaultdict

etcd = etcd3.client(host='10.0.1.215', port=2379)
N_PARTS = 3
HOSTS = ["host-1", "host-2", "host-3"]

def get_prefix_data(prefix):
    data = {}
    for value, metadata in etcd.get_prefix(prefix):
        key = metadata.key.decode("utf-8").split("/")[-1]
        data[key] = json.loads(value.decode("utf-8"))
    return data

def get_links_from_connection_key():
    value, _ = etcd.get("/config/links/connection")
    return json.loads(value.decode("utf-8")) if value else []

def update_satellite_in_etcd(name, sat_data):
    key = f"/config/satellites/{name}"
    etcd.put(key, json.dumps(sat_data))

def main():
    satellites = get_prefix_data("/config/satellites/")
    links = get_links_from_connection_key()

    id_to_name = {sat["ID"]: name for name, sat in satellites.items()}

    G = nx.Graph()
    for name in satellites:
        G.add_node(name)

    for link in links:
        src = id_to_name.get(link["source"])
        dst = id_to_name.get(link["destination"])
        if src and dst:
            G.add_edge(src, dst)

    edgecuts, parts = metis.part_graph(G, nparts=N_PARTS)

    clusters = defaultdict(list)
    for node, part in zip(G.nodes(), parts):
        clusters[part].append(node)

    group_to_host = {i: HOSTS[i] for i in range(N_PARTS)}

    for group_id, sat_names in clusters.items():
        host = group_to_host[group_id]
        for sat in sat_names:
            satellites[sat]["host"] = host
            update_satellite_in_etcd(sat, satellites[sat])

    print("Satellite host assignments updated:")
    for group_id in range(N_PARTS):
        host = group_to_host[group_id]
        print(f"\n{host} ← {len(clusters[group_id])} satellites:")
        for sat in sorted(clusters[group_id]):
            print(f"  - {sat}")

if __name__ == "__main__":
    main()
