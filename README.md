Using Mininet to reproduce Latency vs. Initial Congestion Window Graph
======================================================================

Joe Marama and Jack Dubie
-------------------------

In [An Argument for Increasing TCP’s Initial Congestion Window](https://developers.google.com/speed/articles/tcp_initcwnd_paper.pdf),
Nandita Dukkipati examines the speed to run a Google Web search (download a
file ~15kB from Googles server) while the remote host varies its initial
congestion window.

### Instructions to reproduce our experiement:

Spin up our EC2 image in the AWS management console web application. AMI: `ami-0a339263`

ssh into that server (replace domain name with your instance's domain name)

    ssh -l ubuntu ec2-xxx-xxx-xxx-xxxx.compute-1.amazonaws.com

Install ethstats

    sudo apt-get install ethstats

Clone our repo

    git clone https://github.com/jdubie/mininet-tcp-initial-cwnd.git
    cd mininet-tcp-initial-cwnd

Start open openvswitch

    sudo ./start_openswitch.sh

Reproduce the initcwnd verification figure

    sudo ./icwnd_vs_fct.py

Finally run the experiment

    sudo ./bw_improvement.py

* Results will be printed to stdout and in `results/mininet_yours/latencies.txt`
* scp `results/mininet_yours/latencies.pdf` to your local computer for a bar graph.
