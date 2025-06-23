import etcd3
import json
import subprocess
import random
import time
import os
import csv
import matplotlib.pyplot as plt
from statistics import mean
import threading

etcd = etcd3.client(host='10.0.1.215', port=2379)

def get_prefix_data(prefix):
    data = {}
    for value, meta in etcd.get_prefix(prefix):
        key = meta.key.decode('utf-8').split('/')[-1]
        data[key] = json.loads(value.decode('utf-8'))
    return data

def get_links_from_connection_key():
    value, _ = etcd.get('/config/links/connection')
    if value:
        return json.loads(value.decode('utf-8'))
    return []

def get_sat_host_map():
    sat_map = {}
    for sat, meta in satellites.items():
        host = meta.get('host')
        if host:
            sat_map[sat] = hosts.get(host, {})
    return sat_map

def get_unique_links(links, max_count):
    selected = []
    used_sats = set()
    for link in random.sample(links, len(links)):
        src, dst = link[0], link[1]
        if src not in used_sats and dst not in used_sats:
            selected.append(link)
            used_sats.update([src, dst])
        if len(selected) >= max_count:
            break
    return selected

satellites = get_prefix_data('/config/satellites/')
hosts = get_prefix_data('/config/hosts/')
links_raw = get_links_from_connection_key()
sat_host_map = get_sat_host_map()

valid_links = []
for link in links_raw:
    src, dst = link.get('src_sat'), link.get('dst_sat')
    src_ip, dst_ip = link.get('src_ip'), link.get('dst_ip')
    if not all([src, dst, src_ip, dst_ip]):
        continue
    if src not in satellites or dst not in satellites:
        continue
    if src not in sat_host_map or dst not in sat_host_map:
        continue
    valid_links.append((src, dst, src_ip, dst_ip))

if not valid_links:
    raise RuntimeError("❌ No valid satellite links with IPs found in etcd.")

WORKER_COUNTS = list(range(2, 22))
DURATION = 30
RESULTS = []

OUTPUT_DIR = "/home/ubuntu/dadras/old"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "iperf_logs"), exist_ok=True)

fixed_link_pool = get_unique_links(valid_links, max(WORKER_COUNTS))

def run_iperf_client(idx, src, dst, src_ip, dst_ip, worker_count):
    iteration = worker_count
    src_host = sat_host_map[src]
    dst_host = sat_host_map[dst]

    subprocess.run(["ssh", f"{src_host['ssh_user']}@{src_host['ip']}", "docker", "exec", src, "pkill", "-f", "iperf3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["ssh", f"{dst_host['ssh_user']}@{dst_host['ip']}", "docker", "exec", dst, "pkill", "-f", "iperf3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.Popen(["ssh", f"{dst_host['ssh_user']}@{dst_host['ip']}", "docker", "exec", dst, "iperf3", "-s", "-D"])
    time.sleep(5)

    # Run iperf3 with multiple parallel streams
    cmd = ["ssh", f"{src_host['ssh_user']}@{src_host['ip']}",
           "docker", "exec", src, "iperf3", "-c", dst_ip,
           "-t", str(DURATION), "-P", "40", "--json"]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()

    try:
        output = json.loads(stdout.decode('utf-8'))
        sum_sent = output.get('end', {}).get('sum_sent')
        if not sum_sent or 'bits_per_second' not in sum_sent:
            raise ValueError("Missing 'sum_sent' in iperf3 output")

        bits_per_sec = sum_sent['bits_per_second']
        mbps = bits_per_sec / 1e6
        print(f"    ✅ {src} → {dst}: {mbps:.2f} Mbps")

        log_path = os.path.join(OUTPUT_DIR, "iperf_logs", f"{src}_to_{dst}_workers{worker_count}.json")
        with open(log_path, "w") as f:
            json.dump(output, f, indent=2)

        RESULTS.append({"iteration": iteration, "worker_count": worker_count, "worker": idx+1, "src": src, "dst": dst, "throughput_mbps": mbps})
    except Exception as e:
        print(f"    ⚠️ Worker {idx+1} failed: {e}")
        with open(os.path.join(OUTPUT_DIR, f"error_worker_{idx+1}.log"), "wb") as f:
            f.write(stderr)

for WORKER_COUNT in WORKER_COUNTS:
    print(f"\n⏱ Running test with {WORKER_COUNT} workers...")
    selected_links = fixed_link_pool[:WORKER_COUNT]

    threads = []
    for idx, (src, dst, src_ip, dst_ip) in enumerate(selected_links):
        print(f"  Worker {idx+1}: {src} → {dst}")
        t = threading.Thread(target=run_iperf_client, args=(idx, src, dst, src_ip, dst_ip, WORKER_COUNT))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    avg_total = sum(r['throughput_mbps'] for r in RESULTS if r['worker_count'] == WORKER_COUNT)
    print(f"  ✅ Total throughput ({WORKER_COUNT} workers): {avg_total:.2f} Mbps")

csv_path = os.path.join(OUTPUT_DIR, "throughput_results.csv")
with open(csv_path, "w", newline='') as csvfile:
    fieldnames = ["iteration", "worker_count", "worker", "src", "dst", "throughput_mbps"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in RESULTS:
        writer.writerow(row)

summary = {}
for row in RESULTS:
    key = row['worker_count']
    summary[key] = summary.get(key, 0) + row['throughput_mbps']

x_vals = sorted(summary.keys())
y_vals = [summary[k] for k in x_vals]

plt.figure(figsize=(10, 6))
plt.plot(x_vals, y_vals, marker='o')
plt.title("Total Throughput vs Number of Workers")
plt.xlabel("Number of Workers")
plt.ylabel("Total Throughput (Mbps)")
plt.grid(True)
plt.tight_layout()

plot_path = os.path.join(OUTPUT_DIR, "throughput_plot.png")
plt.savefig(plot_path)
print(f"\n📊 Finished all tests. Results and plot written to {csv_path} and {plot_path}")
