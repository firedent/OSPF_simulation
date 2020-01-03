# OSPF simulation

This project is going to simulating a router protocol. According to the spec, this protocol should be similar to OSPF(Open Shortest Path First). This programe should implete four things.

1. Broadcast the LSDB(Link State Database) of itself
2. Forward the LSDB of others and filter those received before for avoiding boardcast storm.
3. Dealing with some nodes disconnect and reconnect.
4. Update the LSDB in a fixed period and compute the shortest path to each other nodes as soon as the LSDB is updated.

This repo implements all requirements and get full marks.
