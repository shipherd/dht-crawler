# dht-crawler
A simple DHT Network Crawler implemented with Python

Around 100K Hashes per day. 

crawler.py -> The main script (Uses sqlite3 to store hashes).

*.dat -> aria2 Routing Nodes

Please note that this crawler is not Memory Optimized. Running the crawler for too long can lead to Memory Shortage. Also, this crawler uses aria2 to download the torrent files. Please configure your own aria2 downloader.

P.S. aria2 is not a good choice for large amount of file downloading (it eats Memory very quick!), implementing the Torrent File Exchange Protocal on your own is the best choice.
