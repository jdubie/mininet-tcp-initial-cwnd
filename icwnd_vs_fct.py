#!/usr/bin/env python

"CS244 Assignment 3: Baseline for experiments"

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, output
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange, custom, quietRun, dumpNetConnections
from mininet.cli import CLI

from time import sleep, time
from multiprocessing import Process
from subprocess import Popen
import termcolor as T
import argparse

import pyx


import sys
import os
import re
from util.monitor import monitor_devs_ng

parser = argparse.ArgumentParser(description="Baseline tests")

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    default="results")

parser.add_argument('--target', '-g',
                    help="Thing to get",
                    default=27)
                    #default="payloads/google_search.html")

parser.add_argument('--bw_net', '-b',
                    type = float,
                    help="Bandwidth of network",
                    default="1.2")

parser.add_argument('--latency', '-l',
                    help="Latency of network",
                    default="70ms")

parser.add_argument('--cli', '-c',
                    action='store_true',
                    help='Run CLI for topology debugging purposes')

parser.add_argument('--numruns', '-n',
                    type=int,
                    default=3)

parser.add_argument('--time', '-t',
                    dest="time",
                    type=int,
                    help="Duration of the experiment.",
                    default=60)


# Expt parameters
args = parser.parse_args()

if not os.path.exists(args.dir):
    os.makedirs(args.dir)

RESULTS_DIR = args.dir + '/mininet/'

if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

lg.setLogLevel('info')

### print in pretty colors
def cprint(s, color, cr=True):
    """Print in color
       s: string to print
       color: color to use"""
    if cr:
        print T.colored(s, color)
    else:
        print T.colored(s, color),

# Topology to be instantiated in Mininet
class SimpleTopo(Topo):
    "Simple Client Server Topology"

    # lets just assume that default bandwidth 
    # and latency are identical to the averages of
    # the 'avgDC' used in googles paper

    def __init__(self, cpu=.5, bw=args.bw_net, delay=args.latency,
                 max_queue_size=None, **params):
        """client server topology with one receiver
           and 1 clients.
           cpu: system fraction for each host
           bw: link bandwidth in Mb/s
           delay: link delay (e.g. 10ms)
        """

        # Initialize topo
        Topo.__init__(self, **params)

        # Host and link configuration
        client_lconfig = {'bw': bw, 'delay': delay,
                   'max_queue_size': max_queue_size }

        # Create the actual topology
        client = self.add_host('client')
        server = self.add_host('server')
        switch = self.add_switch('s1')

        # Add links
        self.add_link(client, switch, port1=0, port2=1)
        self.add_link(server, switch, port1=0, port2=2, **client_lconfig)


def parse_ping(ping):

    latencies = []

    for ln in ping.split('\n'):
        s = ln.split('time=')
        if len(s) > 1:
            s = s[1].split(' ms')[0]
            latencies.append(float(s))

    return latencies


def verify_latency(net):

    cprint ("*** Verifying Latency ***", 'green')

    h1 = net.getNodeByName('server')
    h2 = net.getNodeByName('client')

    h1_ip = h1.IP()

    result = h2.cmd("ping -c 2 %s" % h1_ip)

    print result
    latency = parse_ping(result)
    print latency
    avg_latency = sum(latency)/len(latency)
    cprint(" Average latency is %f" % avg_latency, 'blue') 

    if abs(avg_latency - 70) > 1:
        cprint ("*** Bad average latency: %d ***" % avg_latency, 'red')
        raise NameError('Latency assertion failed')

    cprint ("*** Latency Dialed in ***", 'green')

    pass

def verify_bandwidth(net):

    receiver = net.getNodeByName('client')
    sender = net.getNodeByName('server')
    switch = net.getNodeByName('s1')
    rec_ip = receiver.IP()

    # run iperf with udp blasting packets at 1gb/s 
    # for 10 seconds to saturate links
    print 'Starting iperf to verify bandwidth....'
    receiver.cmd('iperf -t 10 -s -u > /tmp/rec_iperf &')
    sender.cmd('iperf -t 10 -u -c %s -b 1000000000 > /tmp/send_iperf &' % rec_ip)
    sleep( 2 )

    # take the eth stats of the switch, pipe the sending rate to receiver to file
    # tests how fast the bottleneck link is sending and receiving host is receiving
    print 'Taking stats......'
    switch.cmd('ethstats > /tmp/switch_band &')
    receiver.cmd('ethstats > /tmp/rec_band &')
    sleep( 2 )

    # kill zombies!
    print 'Killing bandwidth tests.... '
    switch.cmd('kill %ethstats')
    receiver.cmd('kill %iperf')
    sender.cmd('kill %iperf')

    # extract bandwidth at switch's sending port and receivers receiving port
    sw_f = open('/tmp/switch_band')
    switch_bw = float( re.findall("\d+.\d+", sw_f.readlines()[3] )[1] ) 
    rec_f = open('/tmp/rec_band')
    rec_bw = float( re.findall("\d+.\d+", rec_f.readline() )[0] ) 
    print 'switch bandwidth =', switch_bw, 'Mb/s\trecievers bandwidth =', rec_bw, 'Mb/s'

    if abs(switch_bw - args.bw_net) > 2 or abs(rec_bw - args.bw_net) > 2:
        cprint('BANDWIDTH TEST FAILED, EXITING NOW!!!', 'red')
        net.stop()
        sys.exit(1)
    else:
        cprint('Bandwidth test passed!\n', 'green')



def query_server(client, serv_ip, run_num):

    # execute command!
    wget_res = client.cmd('time (wget %s:8000/%s -o /tmp/wget%d -P /tmp/%d) 2> %s/wgettime%d ' % 
            (serv_ip, args.target, run_num, run_num, args.dir, run_num))

    # extract and return real time as reported by time
    a = open(r"%s/wgettime%d" % (args.dir, run_num), "r")
    for line in a:
        if line.startswith("real"):
            return float( re.findall("\d*\\.\d*", line)[0] ) 

    # return nothing if nothing is found
    return None


def start_server(net):
    "Start the simple python http server"

    server = net.getNodeByName('server')
    cprint("starting the server...", "green")

    result = server.cmd('nohup python -m lib/SimpleVarLengthHTTPServer > %s/serverlog.txt &' % args.dir)

    # Have to sleep for a little to allow the server to spin up
    # TODO - can we make this a little less hacky?
    sleep(1)

def start_tcpprobe():
    os.system("rmmod tcp_probe &>/dev/null; modprobe tcp_probe;")
    Popen("cat /proc/net/tcpprobe > %s/tcp_probe.txt" % args.dir, shell=True)

def stop_tcpprobe():
    os.system("killall -9 cat; rmmod tcp_probe &>/dev/null;")

def increase_client_rwnd(net):
    """
    Simple set of commands to increase the receivers
    initial receieve window high enough to never be the
    initial limiting factor
    """

    client = net.getNodeByName('client')
    cli_route = client.cmd("ip route")
    cli_route = cli_route.replace('\n', ' ')
    cli_res = client.cmd("ip route change %s initcwnd 45 initrwnd 45" % (cli_route))
    client.cmd("ip route flush cache")


def verify_cwnd(net, cwnd):
    "Verify the initial congestion window"

    # Get server and client
    cprint("verifying the initial cwnd.... ", "green")
    server = net.getNodeByName('server')
    client = net.getNodeByName('client')

    # Start tcpprobe, server, then client
    start_tcpprobe()
    cprint("verifying the initial cwnd.... ", "green")
    server.cmd("iperf -s -Z reno -p 5001 > /dev/null &")
    iperf_res = client.cmd("iperf -c %s -Z reno -p 5001 -t 3 > /dev/null" % server.IP())
    sleep(3)
    
    # stop iperf once client is done
    os.system("killall -9 iperf")
    stop_tcpprobe()

    # verify the initial cwnd
    pfile = open("%s/tcp_probe.txt" % args.dir, "r")
    line_comps = pfile.readline().split(' ')
    if len(line_comps) < 7:
      cprint(">>>>>>>> verify_cwnd failed! returning <<<<<< ", "red")
      return

    obs_cwnd = int(line_comps[6])
    cprint(">>>>>>>>>>  OBSERVED CWND = %d <<<<<<<<<<<" % obs_cwnd, "yellow")
    if abs(cwnd - obs_cwnd) > 1:
        cprint(">>>>>>> ITS TOO FAR FROM THE SET VALUE! <<<<<<<<<<", "red")

def run_simple_exp(net, num_runs):
    "Run experiment"

    seconds = args.time

    # Get server and client
    server = net.getNodeByName('server')
    client = net.getNodeByName('client')
    server.cmd("clear")
    client.cmd("clear")
    serv_ip = server.IP()
    cli_ip = client.IP()
    serv_route = server.cmd("ip route")
    cli_route = client.cmd("ip route")
    serv_route = serv_route.replace('\n', ' ')
    cli_route = cli_route.replace('\n', ' ')
    print serv_route
    print cli_route

    # have the client get the server's web page
    cprint("starting the client's requests", "green")

    cwnd_times = []
    latencies = []
    cwnds = [3, 6, 10, 16, 26, 42]
    #cwnds = [1, 20]

    for cwnd in cwnds:

        #change congestion windows
        sleep(0.5)
        print "testing for cwnd of size %d ...." % cwnd

        server.cmd("clear")
        serv_res = server.cmd("ip route change %s initcwnd %d cwnd %d" % (serv_route, cwnd, cwnd))
        #print "server results from ip route change ..... ", serv_res
        server.cmd("ip route flush cache")

        # verify cwnds 
        #serv_v = server.cmd("ip route")
        #print "server ip route listing --->>>> ", serv_v
        #serv_r = server.cmd("ip route get %s" % cli_ip)
        #print "server route = ", serv_r
        #cli_r = client.cmd("ip route get %s" % serv_ip)
        #print "client route = ", cli_r
        #verify_cwnd(net, cwnd) # TODO - doesn't really work

        # test wget times
        times = []
        for r in range(num_runs):
            cprint("%d ..." % (r + 1), "green")

            times.append( query_server(client, serv_ip, r) )

            sleep(0.5) # TODO - why are we getting those spurious times? this works fine

        avg_time = sum(times)/len(times)
        latency = int(avg_time * 1000)
        print times, " -- avg time -- ", avg_time, "ms"
        print " -- latency -- ", latency, "ms"
        cwnd_times.append(avg_time)
        latencies.append(latency)

    #print cwnd_times
    save_graph(cwnds,latencies)
    
def save_graph(cwnds,latencies):

    assert(len(cwnds) == len(latencies))
    
    # write .dat file
    to_file = ''
    cprint('*****************', 'cyan')
    cprint('**** RESULTS ****', 'cyan')
    cprint('*****************', 'cyan')
    cprint('CWND  LATENCY', 'cyan')
    for i in range(0,len(cwnds)):
      line = '{0:4d}  {1:3d}'.format(cwnds[i],latencies[i])
      cprint(line, 'cyan')
      to_file += line + '\n'
    f = open(RESULTS_DIR + 'latencies.dat', 'w')
    f.write(to_file)
    f.close()
    cprint ('*****************', 'cyan')
    cprint ('** END RESULTS **', 'cyan')
    cprint ('*****************', 'cyan')

    # create graph
    mypainter = pyx.graph.axis.painter.bar(nameattrs=[pyx.trafo.rotate(45),
                                                  pyx.text.halign.right],
                                       innerticklength=0.1)
    myaxis = pyx.graph.axis.bar(painter=mypainter)

    g = pyx.graph.graphxy(width=8, x=myaxis)
    g.plot(pyx.graph.data.file(RESULTS_DIR + 'latencies.dat', xname=1, y=2), [pyx.graph.style.bar()])
    g.writeEPSfile(RESULTS_DIR + 'latencies')
    g.writePDFfile(RESULTS_DIR + 'latencies')


def main():
    "Create and run experiment"
    start = time()

    topo = SimpleTopo()

    # create very simple mininet
    net = Mininet(topo=topo, link=TCLink)

    net.start()

    # increase clients rwnd before anything else
    increase_client_rwnd(net)
    
    # test stuff before starting
    cprint("*** Dumping network connections:", "green")
    dumpNetConnections(net)

    cprint("*** Testing connectivity", "blue")
    net.pingAll()

   # verify_latency(net) 
    sleep(2)
   # verify_bandwidth(net)

    if args.cli:
        # Run CLI instead of experiment
        CLI(net)

    # start server
    start_server(net)

    #run simple experiment
    run_simple_exp(net, args.numruns)

    # client before and after to track changes
    if args.cli:
        # Run CLI instead of experiment
        CLI(net)

    # end the experiment, output stats
    net.stop()
    end = time()
    cprint("Experiment took %.3f seconds" % (end - start), "yellow")


if __name__ == '__main__':
    main()

