import os
import sys
import argparse
import netaddr
from netaddr import EUI

def _parse_args( args_str):
    parser = argparse.ArgumentParser()
    args, remaining_argv = parser.parse_known_args(args_str.split())
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

def get_subnet_iter_obj_for_static_route(subnet='1.1.1.0/24'):
    addr,prefix = subnet.split('/')
    ad1,ad2,ad3,ad4 = addr.split('.')
    return iter([str(int(ad1)+x)+'.'+ad2+'.'+ad3+'.'+ad4+'/'+prefix for x in range(1,250)])

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
    static_route_subnet = get_subnet_iter_obj_for_static_route(subnet='2.0.1.0/24')
    for vlan in vlans:
        try:    
            m_addr = mac.next()
            sub = subnet.next()
            static_route_sub = static_route_subnet.next()
        except StopIteration:
            return
        vn_name = get_vn_name(script_args.start_vn_name,vlan)
        os.system("python vmi.py --static_route_subnet %s\
                          --tenant_id %s\
                          --config_node_ip %s\
                          --vcenter_vm_mac %s\
                          --vn_name %s\
                          --subnet %s\
                          --auth_url %s"
                          %(static_route_sub,
                           script_args.tenant_id,
                           script_args.config_node_ip,
                           m_addr,vn_name,sub,
                           script_args.auth_url 
                           )
                         )



#python vmi_scale.py  --tenant_id 74ebcac4-21da-4fe3-8c7f-e84c9e0424ca --config_node_ip 192.168.192.60 --start_mac 000029572113 --start_vn_name tor_vn_ --start_vlan   6 --number_of_vlan 7 --auth_url http://10.204.217.144:5000/v2.0
if __name__ == "__main__":
    main()

