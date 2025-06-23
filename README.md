#  Satellite Network Emulator

This repository builds a scalable, testable simulation of a satellite network using Docker, VXLAN tunnels, and iperf3-based ECMP routing analysis. It includes automation scripts, link creation, container setup, and performance testing.

---

##  FILE-BY-FILE EXPLANATION

### `sat-agent.py`  (Main Orchestrator)

Automates the full satellite network setup:

* Reads configs from `etcd`
* Creates Docker containers for satellites (`create-sat.sh`)
* Builds VXLAN links between satellites (`add-link.sh`)
* Assigns IPs and shapes bandwidth (`add-sat-address.sh`)
* Updates topology in etcd with enriched metadata

### `create-sat.sh` 

Creates a Docker container for a satellite and connects it to a bridge network.

### `add-link.sh` 

Creates a VXLAN tunnel between two satellite containers, complete with bandwidth shaping for ECMP fairness (2 Mbps).

### `add-sat-address.sh` 

Assigns IP addresses to each satellite's antenna interfaces (`br1`, `br2`, ...) and applies traffic shaping.

### `create_bridges.sh` 

Sets up Linux bridge interfaces `br1` to `br5` on each host. Needed for linking VXLANs inside Docker.

### `configure_frr_isis.sh` 

Applies FRRouting IS-IS configuration to satellites. Adds loopbacks, redistributes static routes, configures adjacency.

### `Clustering-metis.py` 

Performs graph partitioning to assign satellites to hosts. Updates `/config/satellites/` in etcd.

### `network_test_scenarios-9-ecmp40hashflows.py` 

Runs iperf3 tests on active links:

* Spawns up to 20 parallel clients
* Measures throughput
* Saves results to CSV
* Generates a throughput-vs-worker plot

### `Leo200.json` 

Sample route data used for predefined hop-based traffic simulation.

### `image.dockerfile` 

Dockerfile to build the `shahramdd/sat:3.4` image for satellite containers (includes iperf3, FRR, etc).

---

## 🧳 HOW `sat-agent.py` APPLIES SCRIPTS (STEP-BY-STEP)

| Step | Description                                 | Script                       |
| ---- | ------------------------------------------- | ---------------------------- |
| 1️⃣  | Read satellite and host data                | `etcd.get_prefix()`          |
| 2️⃣  | Create Docker containers                    | `create-sat.sh`              |
| 3️⃣  | Build VXLAN tunnels                         | `add-link.sh`                |
| 4️⃣  | Assign IP addresses                         | `add-sat-address.sh`         |
| 5️⃣  | Enrich etcd topology with interface/IP info | Inlined                      |
| 6️⃣  | (Optional) Configure IS-IS routing          | `configure_frr_isis.sh`      |
| 7️⃣  | (Optional) Run throughput test              | `network_test_scenarios*.py` |

---

## HOW TO RUN

### 1. Retrieve Desired State from etcd

* Ensure the following keys exist in etcd:

  * `/config/satellites/`
  * `/config/hosts/`
  * `/config/links/connection`

### 2. Launch Agent

```bash
python3 sat-agent.py
```

### 3. Create Bridges and Containers Across Hosts

* Bridges (`br1` to `br5`) are created on each host.
* Satellites are assigned to hosts using METIS-based clustering via `Clustering-metis.py`.

### 4. Deploy Network and Create VXLAN Links

* VXLAN tunnels are created between satellite containers.
* `tc` traffic shaping is applied (2 Mbps per interface).

### 5. Assign IP Addresses and Apply Traffic Control

* Each antenna interface receives a `/32` IP.
* Traffic shaping is applied to all interfaces including `eth0`.

### 6. Configure IS-IS and FRR (Optional)

```bash
./configure_frr_isis.sh <SAT_NAME> <NET_ID> <ANTENNAS...> <SAT_CIDR> [HOST] [USER]
```

### 7. Run Performance Test

```bash
python3 network_test_scenarios-9-ecmp40hashflows.py
```

### 8. OUTPUT

* **CSV**: Worker-wise throughput details
* **Plot**: Throughput trend as number of workers increases
* **Log Files**: JSON logs of each iperf3 session

---

## 🔹 OUTPUT

* **CSV**: Worker-wise throughput details
* **Plot**: Throughput trend as number of workers increases
* **Log files**: JSON logs of each iperf3 session

