#!/bin/bash
# TernOO Onion appliance — air-gapped Tor netns. ALL traffic in 'torns' -> Tor; no leak path.
NS=torns; HOSTIP=10.200.0.1; NSIP=10.200.0.2; TRANS=9040; DNSP=5353
ip netns del $NS 2>/dev/null; ip link del tor0 2>/dev/null
ip netns add $NS
ip link add tor0 type veth peer name tor1
ip link set tor1 netns $NS
ip addr add $HOSTIP/24 dev tor0; ip link set tor0 up
ip netns exec $NS ip addr add $NSIP/24 dev tor1
ip netns exec $NS ip link set tor1 up
ip netns exec $NS ip link set lo up
ip netns exec $NS ip route add default via $HOSTIP
ip netns exec $NS sysctl -qw net.ipv6.conf.all.disable_ipv6=1
ip netns exec $NS sysctl -qw net.ipv6.conf.default.disable_ipv6=1
mkdir -p /etc/netns/$NS; echo "nameserver $HOSTIP" > /etc/netns/$NS/resolv.conf
grep -q "TransPort $HOSTIP:$TRANS" /etc/tor/torrc || sed -i "s/^TransPort .*/TransPort $HOSTIP:$TRANS/; s/^DNSPort .*/DNSPort $HOSTIP:$DNSP/" /etc/tor/torrc
systemctl reload tor 2>/dev/null || systemctl restart tor
iptables -t nat -N TORNS 2>/dev/null; iptables -t nat -F TORNS
iptables -t nat -C PREROUTING -i tor0 -j TORNS 2>/dev/null || iptables -t nat -A PREROUTING -i tor0 -j TORNS
iptables -t nat -A TORNS -p udp --dport 53 -j REDIRECT --to-ports $DNSP
iptables -t nat -A TORNS -p tcp --dport 53 -j REDIRECT --to-ports $DNSP
iptables -t nat -A TORNS -p tcp --syn -j REDIRECT --to-ports $TRANS
iptables -C FORWARD -i tor0 -j DROP 2>/dev/null || iptables -A FORWARD -i tor0 -j DROP
echo "torns up"
