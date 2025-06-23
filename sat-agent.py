import etcd3
import subprocess
import json
import os

LOCAL_HOST = "host-1"
etcd = etcd3.client(host='10.0.1.215', port=2379)

def get_prefix_data(prefix):
    data = {}
    for value, metadata in etcd.get_prefix(prefix):
        key = metadata.key.decode('utf-8').split('/')[-1]
        data[key] = json.loads(value.decode('utf-8'))
    return data

def get_links_from_connection_key():
    value, _ = etcd.get('/config/links/connection')
    if value:
        return json.loads(value.decode('utf-8'))
    return []

satellites = get_prefix_data('/config/satellites/')
links = get_links_from_connection_key()
hosts = get_prefix_data('/config/hosts/')

print(f"🚀  Found satellites: {list(satellites.keys())}")
print(f"🔗 Found links: {len(links)}")

# === STEP 1: Create satellites ===
for name, sat in satellites.items():
    print(f"➞️ Creating satellite: {name}")
    host_info = hosts[sat['host']]
    ssh_user = host_info['ssh_user']
    cmd = ['./create-sat.sh', name, str(sat['n_interfaces']), sat['host'], ssh_user]
    subprocess.run(cmd, check=True)

# === STEP 2: Create VXLAN links ===
sat_id_to_name = {sat["ID"]: name for name, sat in satellites.items()}
used_antennas = {name: set() for name in satellites}

for link in links:
    src_id = link['source']
    dst_id = link['destination']

    src_name = sat_id_to_name.get(src_id)
    dst_name = sat_id_to_name.get(dst_id)

    if not src_name or not dst_name:
        print(f"⚠️ Skipping link: unknown satellite IDs ({src_id} → {dst_id})")
        continue

    src_used = used_antennas[src_name]
    dst_used = used_antennas[dst_name]

    src_antenna = next((i for i in range(1, 5) if i not in src_used), None)
    dst_antenna = next((i for i in range(1, 5) if i not in dst_used), None)

    if src_antenna is None or dst_antenna is None:
        print(f"❌ Skipping link {src_name} → {dst_name}: no free antennas")
        continue

    used_antennas[src_name].add(src_antenna)
    used_antennas[dst_name].add(dst_antenna)

    src_host = satellites[src_name]['host']
    dst_host = satellites[dst_name]['host']
    ssh_user = hosts[src_host]['ssh_user']

    # Interface naming and enrichment
    src_interface = f"{dst_name}_a{dst_antenna}"
    dst_interface = f"{src_name}_a{src_antenna}"

    print(f"🔗 Creating VXLAN: {src_name}.a{src_antenna} → {dst_name}.a{dst_antenna}")

    link_cmd = ['./add-link.sh', src_name, str(src_antenna),
                src_host, dst_name, str(dst_antenna),
                dst_host, ssh_user]
    subprocess.run(link_cmd, check=True)

    # Enrich link data for etcd
    link['src_sat'] = src_name
    link['dst_sat'] = dst_name
    link['src_antenna'] = src_antenna
    link['dst_antenna'] = dst_antenna
    link['src_interface'] = src_interface
    link['dst_interface'] = dst_interface

# === STEP 3: Assign satellite IP addresses ===
for name, sat in satellites.items():
    print(f"🌐 Assigning IPs for satellite: {name}")

    if 'sat_net_cidr' not in sat:
        sat_id = int(sat.get('ID', 0))
        sat['sat_net_cidr'] = f"192.168.{sat_id}.0/24"
        print(f"ℹ️  Auto-assigned sat_net_cidr: {sat['sat_net_cidr']}")

    host_info = hosts[sat['host']]
    ssh_user = host_info['ssh_user']

    ip_cmd = ['./add-sat-addresses.sh', name, str(sat['n_interfaces']),
              sat['sat_net_cidr'], sat['host'], ssh_user]
    subprocess.run(ip_cmd, check=True)

# === STEP 4: Add IP addresses to enriched links ===
for link in links:
    src_name = link['src_sat']
    dst_name = link['dst_sat']
    src_antenna = link['src_antenna']
    dst_antenna = link['dst_antenna']

    src_ip = f"192.168.{satellites[src_name]['ID']}.{src_antenna}"
    dst_ip = f"192.168.{satellites[dst_name]['ID']}.{dst_antenna}"

    link['src_ip'] = src_ip
    link['dst_ip'] = dst_ip

# === STEP 5: Configure IS-IS ===
isis_interfaces = {}
for link in links:
    for sat_key, ant_key in [('src_sat', 'src_antenna'), ('dst_sat', 'dst_antenna')]:
        sat = link[sat_key]
        antenna = str(link[ant_key])
        isis_interfaces.setdefault(sat, set()).add(antenna)

for sat_name, antennas in isis_interfaces.items():
    sat = satellites.get(sat_name, {})
    sat['net_id'] = sat.get('net_id', f"{int(sat.get('ID', 0)):04d}")
    sat_cidr = sat['sat_net_cidr']
    host_info = hosts[sat['host']]
    ssh_user = host_info['ssh_user']

    print(f"📱 Configuring IS-IS for {sat_name} on antennas {sorted(antennas, key=int)}")

    isis_cmd = ['./configure-isis.sh', sat_name, sat['net_id'],
                *sorted(antennas, key=int), sat_cidr, sat['host'], ssh_user]
    subprocess.run(isis_cmd, check=True)

# === STEP 6: Write updated links to etcd ===
etcd.put('/config/links/connection', json.dumps(links))
print("✅ Full satellite setup and configuration completed.")
