Using Mininet to reproduce Latency vs. Initial Congestion Window Graph
======================================================================

Joe Marama and Jack Dubie
-------------------------

In [An Argument for Increasing TCP’s Initial Congestion Window](https://developers.google.com/speed/articles/tcp_initcwnd_paper.pdf),
Nandita Dukkipati examines the speed to run a Google Web search (download a
file ~15kB from Googles server) while the remote host varies its initial
congestion window.

Clone our repo

  git clone https://github.com/jdubie/mininet-tcp-initial-cwnd.git
  cd mininet-tcp-initial-cwnd

Start open openvswitch

  sudo ./start_openswitch.sh

Finally run the experiment

  sudo ./run_experiment.py

To see the results open `results/mininet_yours/latencies.txt` or scp
`results/mininet_yours/latencies.pdf` to your local computer.



