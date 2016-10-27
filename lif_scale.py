import os
import sys
import argparse
import netaddr
from netaddr import EUI

def _parse_args( args_str):
    parser = argparse.ArgumentParser()
    args, remaining_argv = parser.parse_known_args(args_str.split())
    parser.add_argument(
                "--physical_interfaces_id", nargs='+', help="Physical interface id",required=True)
    parser.add_argument(
                "--username", nargs='?', default="admin",help="User name")
    parser.add_argument(
                "--password", nargs='?', default="contrail123",help="password")
    parser.add_argument(
                "--tenant_id", nargs='?', help="trnant id",required=True)
    parser.add_argument(
                "--config_node_port", help="config node port")
    parser.add_argument(
                "--config_node_ip",  help="config node ip",required=True)
    parser.add_argument(
                "--physical_router_id",  help="Physical router id")
    parser.add_argument(
                "--start_mac",  help="Mac address of vcenter vm ",required=True)
    parser.add_argument(
                "--start_vn_name", help="Vn name to launch vmi",required=True)
    parser.add_argument(
                "--start_vlan",  help="Initial vlan",required=True)
    parser.add_argument(
                "--number_of_vlan",  help="number of vlans to be created",required=True)
    parser.add_argument(
                "--auth_url", nargs='?', default="check_string_for_empty",help="Auth Url",required=True)
    args = parser.parse_args(remaining_argv)
    return args

def get_mac_address_iter_obj(mac,start_range,end_range):
    return iter(["{:012X}".format(int(mac, 16) + x) for x in range(int(start_range),int(end_range)+1)])

def get_subnet_iter_obj(subnet='1.1.1.0/24'):
    addr,prefix = subnet.split('/')
    ad1,ad2,ad3,ad4 = addr.split('.')
    return iter([ad1+'.'+str(int(ad2)+x)+'.'+str(int(ad3)+y)+'.'+ad4+'/'+prefix for x in range(1,250) for y in range(1,250)])

def get_vn_name(base_vn_name,counter):
    return base_vn_name + str(counter)

def get_vlan_range(start_vlan,numbers):
    vlan_range=[]
    end_vlan= int(start_vlan) + int(numbers)
    for x in range(int(start_vlan),int(end_vlan)+1):
        vlan_range.append(str(x))
    return vlan_range
        

def main(args_str = None):
    if not args_str:
       script_args = ' '.join(sys.argv[1:])
    script_args = _parse_args(script_args)
    start_vlan = script_args.start_vlan
    number_of_vlan = script_args.number_of_vlan
    vlans = get_vlan_range(start_vlan,number_of_vlan)
    mac = get_mac_address_iter_obj(script_args.start_mac,'0',number_of_vlan)
    subnet = get_subnet_iter_obj()
    for vlan in vlans:
        print "%s"%vlan
        try:    
            m_addr = mac.next()
            sub = subnet.next()
            print "%s %s"%(m_addr,sub)
        except StopIteration:
            return
        lif1 = 'p6p1.' + vlan
        lif2 = 'p6p1.' + vlan
        vn_name = get_vn_name(script_args.start_vn_name,vlan)
        os.system("python lif.py --name %s %s \
                          --physical_interfaces_id %s %s\
                          --tenant_id %s\
                          --config_node_ip %s\
                          --vcenter_vm_mac %s\
                          --vn_name %s\
                          --subnet %s\
                          --vlan %s\
                          --auth_url %s"
                          %(lif1,lif2,
                           script_args.physical_interfaces_id[0], 
                           script_args.physical_interfaces_id[1], 
                           script_args.tenant_id,
                           script_args.config_node_ip,
                           m_addr,vn_name,sub,vlan,
                           script_args.auth_url 
                           )
                         )



#python lif_scale.py  --physical_interfaces_id da6b060e-5ce3-43d6-96b7-7ccab669776a d4db4030-e6e8-4032-baf0-38b74c27ad7f --tenant_id e30e213b-a046-4e4d-a198-98e0c55fb686 --config_node_ip 10.204.217.139 --start_mac 000029572113 --start_vn_name ixia_vlan_ --start_vlan   6 --number_of_vlan 4089 --auth_url http://10.204.217.144:5000/v2.0
if __name__ == "__main__":
    main()

