from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.node import OVSKernelSwitch, RemoteController

class MyTopo(Topo):
    def build(self):
        # Define switches
        switches = {}
        for i in range(1, 7):
            switches[f's{i}'] = self.addSwitch(f's{i}', cls=OVSKernelSwitch, protocols='OpenFlow13')

        # Define hosts
        host_index = 1
        for sw in range(1, 7):
            for j in range(3):
                host_name = f'h{host_index}'
                mac_addr = f"00:00:00:00:00:{host_index:02d}"
                ip_addr = f"10.0.0.{host_index}/24"
                host = self.addHost(host_name, cpu=1.0/20, mac=mac_addr, ip=ip_addr)
                self.addLink(host, switches[f's{sw}'])
                host_index += 1

        # Connect switches linearly
        for i in range(1, 6):
            self.addLink(switches[f's{i}'], switches[f's{i+1}'])

def startNetwork():
    topo = MyTopo()
    net = Mininet(topo=topo, link=TCLink, controller=None)

    # Set up remote controller
    c0 = RemoteController('c0', ip='10.193.17.52', port=6653)
    net.addController(c0)

    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    startNetwork()
