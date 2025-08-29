# README file for the Geo IP map project


### Versions


#### Release 1.0 Basic 
- A bash script is used to build and start two docker containers: 
1. remote: The container sending packets 
2. host: The container receiving packets

- sender (remote container) can read from the SQL lite databases of random countries and their Major IP blocks, append the CIDR mask as a payload, and sent to the receiver (host container).  

- receiver (host container) can read the IP packet, decode the payload, and print the network address + CIDR mask in the payload. 


### Common docker commands
- Run these in the same directory as `docker.sh`

- Build the containers image
```
./docker.sh build
```

- Open the two containers terminals 
```
./docker.sh start
```

- To close and stop both containers
```
docker kill host remote
```

- To check the containers name if the above does not work run: 
```
docker ps
```
- then keep what ever `NAMES` have `scapy_base` under `IMAGE`

- Stop the docker network
```
docker network rm scapy_net
```

- If you break network access again run this: 
```
docker build --network=host -t scapy_base -f proj/Dockerfile.scapy proj
```

- Remove all old docker build aritfacts 
```
docker system prune
```