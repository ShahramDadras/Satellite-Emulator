#!/bin/bash
# Usage:
# ./configure-isis.sh <SRC_SAT> <NET_ID> <ANTENNAS...> <SAT_NET_CIDR> [SAT_HOST] [SSH_USERNAME]

SRC_SAT="$1"
NET_ID="$2"
shift 2

ANTENNAS=()
while [[ "$1" =~ ^[0-9]+$ ]]; do
  ANTENNAS+=("$1")
  shift
done

SAT_NET="$1"
shift

SAT_HOST="host-0"
SSH_USERNAME="$USER"

if [[ $# -gt 0 ]]; then
  SAT_HOST="$1"
  shift
fi

if [[ $# -gt 0 ]]; then
  SSH_USERNAME="$1"
  shift
fi

# Validation
if [[ -z "$SRC_SAT" || -z "$NET_ID" || ${#ANTENNAS[@]} -eq 0 || -z "$SAT_NET" ]]; then
  echo "Usage: $0 <SRC_SAT> <NET_ID> <ANTENNAS...> <SAT_NET> [SAT_HOST] [SSH_USERNAME]"
  exit 1
fi

# host- Area ID extraction
if [[ "$SAT_HOST" =~ host-([0-9]+) ]]; then
  AREA_NUM="${BASH_REMATCH[1]}"
  AREA_ID=$(printf "%04d" "$AREA_NUM")
else
  AREA_ID="0000"
fi

# Extract subnet and loopback IP
CIDR_MASK="${SAT_NET##*/}"
BASE_IP="${SAT_NET%%/*}"
IFS='.' read -r o1 o2 o3 o4 <<< "$BASE_IP"
NET_PREFIX="$o1.$o2.$o3.0/$CIDR_MASK"
LO_IP="$o1.$o2.$o3.254/$CIDR_MASK"
LO_IFACE="lo"
ISIS_NAME="CORE"

# FRR
DAEMONS_CONF=$(cat <<EOF
zebra=yes
isisd=yes
EOF
)

FRR_CONF=$(cat <<EOF
!
hostname $SRC_SAT
password zebra
enable password zebra
!
interface $LO_IFACE
 ip address $LO_IP
 ip router isis $ISIS_NAME
 isis circuit-type level-2
 isis passive-interface
!
router isis $ISIS_NAME
 net 49.$AREA_ID.0000.0000.$NET_ID.00
 is-type level-2
 metric-style wide
 log-adjacency-changes
 address-family ipv4 unicast
  redistribute static
 exit-address-family
!
EOF
)
# Add bridge interfaces (advertise networks on these interfaces)
for antenna in "${ANTENNAS[@]}"; do
  br="br$antenna"
  FRR_CONF+=$'\n'"interface $br"
  FRR_CONF+=$'\n'" ip router isis $ISIS_NAME"
  FRR_CONF+=$'\n'" isis network point-to-point"
  FRR_CONF+=$'\n'" isis metric 2"
  FRR_CONF+=$'\n'"!"
done

#"Static routes are global, define them outside 'router isis' to ensure proper redistribution."

FRR_CONF+=$'\n'"ip route $NET_PREFIX Null0"$'\n'"!"
# Apply config to the satellite
ssh -q "$SSH_USERNAME@$SAT_HOST" bash <<EOF > /dev/null 2>&1
docker exec -i "$SRC_SAT" tee /etc/frr/daemons > /dev/null <<EODAEMONS
$DAEMONS_CONF
EODAEMONS

docker exec -i "$SRC_SAT" tee /etc/frr/frr.conf > /dev/null <<EOFRR
$FRR_CONF
EOFRR

docker exec "$SRC_SAT" ip link set $LO_IFACE up || true
docker exec "$SRC_SAT" chown frr:frr /etc/frr/daemons /etc/frr/frr.conf
docker exec "$SRC_SAT" bash -c "service frr restart || systemctl restart frr" > /dev/null 2>&1
EOF

echo "IS-IS successfully configured on '$SRC_SAT' (area $AREA_ID) and subnet $NET_PREFIX"
