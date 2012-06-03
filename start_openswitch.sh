#!/usr/bin/env bash
cd ~ && cd openvswitch
insmod datapath/linux/openvswitch.ko
ovsdb-server --remote=punix:/usr/local/var/run/openvswitch/db.sock \
                     --remote=db:Open_vSwitch,manager_options \
                     --pidfile --detach

ovs-vsctl --no-wait init
ovs-vswitchd --pidfile --detach

