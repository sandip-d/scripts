import os
import sys
import argparse
from vnc_api.vnc_api import  *
from neutronclient.neutron import client as neutron_client
import uuid
import netaddr
from netaddr import EUI
import subprocess

def _parse_args( args_str):
    parser = argparse.ArgumentParser()
    args, remaining_argv = parser.parse_known_args(args_str.split())
    parser.add_argument(
                "--static_route_subnet", help="static route prefix",required=True)
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
                "--vcenter_vm_mac",  help="Mac address of vcenter vm ",required=True)
    parser.add_argument(
                "--vn_name", help="Vn name to launch vmi",required=True)
    parser.add_argument(
                "--subnet", help="subnet of the vn",required=True)
    parser.add_argument(
                "--auth_url", nargs='?', default="check_string_for_empty",help="Auth Url",required=True)
    args = parser.parse_args(remaining_argv)
    return args

def create_vm(cmd):
    try:
        result = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True)
        return True
    except subprocess.CalledProcessError, OSError:
        print("WARNING: error executing subprocess shell cmd: '%s'" % cmd)
        return False

def get_static_route_subnet(subnet='1.1.1.0/24'):
    addr,prefix = subnet.split('/')
    ad1,ad2,ad3,ad4 = addr.split('.')
    return [ad1+'.'+str(int(ad2)+x)+'.'+str(int(ad3)+y) for x in range(1,250) for y in range(1,250)]

def _parse_subnets(vn_subnets):
    # If the list is just having cidrs
    if vn_subnets and (type(vn_subnets[0]) is str or
                            type(self.vn_subnets[0]) is unicode):
        vn_subnets = [{'cidr': x} for x in vn_subnets]
    return vn_subnets
# end _parse_subnets

def create_subnet(neutron_obj, subnet, net_id, ipam_fq_name=None, enable_dhcp=True, disable_gateway=False):
        subnet_req = subnet
        subnet_req['network_id'] = net_id
        subnet_req['enable_dhcp'] = enable_dhcp
        subnet_req['ip_version'] = '4'
        subnet_req['cidr'] = unicode(subnet_req['cidr'])
        subnet_req['contrail:ipam_fq_name'] = ipam_fq_name
        if disable_gateway:
           subnet_req['gateway_ip'] = None
        try:
            subnet_rsp = neutron_obj.create_subnet({'subnet': subnet_req})
            return subnet_rsp
        except Exception as e:
            return None
    # end _create_subnet 

def _create_vn(vnc, vn_name, vn_subnet,project = None):


    ipam_obj = vnc.network_ipam_read(fq_name = ['default-domain', 'default-project', 'default-network-ipam'])
    vn_obj = VirtualNetwork(vn_name, parent_obj=project)
    pfx = vn_subnet.split('/')[0]
    pfx_len = int(vn_subnet.split('/')[1])
    subnet_vnc = IpamSubnetType(subnet=SubnetType(pfx, pfx_len))
    vnsn_data = VnSubnetsType([subnet_vnc])
    vn_obj.add_network_ipam(ipam_obj, vnsn_data)

    try:
        return vnc.virtual_network_create(vn_obj)
    except RefsExistError:
        return None

def create_network(
            neutron_obj,
            vn_name,
            vn_subnets=None,
            ipam_fq_name=None,
            shared=False,
            router_external=False,
            enable_dhcp = True,
            sriov_enable = False,
            sriov_vlan = None,
            sriov_provider_network = None,
            disable_gateway=False):
        """Create network given a name and a list of subnets.
        """
        vn_subnets=_parse_subnets(vn_subnets)
        try:
            net_req = {}
            net_req['name'] = vn_name
            net_rsp = neutron_obj.create_network({'network': net_req})

            vn_id = net_rsp['network']['id']
            net_id = net_rsp['network']['id']
            if vn_subnets:
                for subnet in vn_subnets:
                    net_rsp = create_subnet(neutron_obj,
                        subnet, net_id, ipam_fq_name, enable_dhcp, disable_gateway)
            # end for
            return neutron_obj.show_network(network=net_id)
        except Exception as e:
            return None

def contrail_create_port(vnc_api_object,project_obj,mac_address,vn_obj,security_groups=None,fixed_ips=None):
    vmi_id = str(uuid.uuid4())
    vmi_obj = VirtualMachineInterface(name=vmi_id,
        parent_obj=project_obj)
    mac_address_obj = MacAddressesType()
    mac_address_obj.set_mac_address([str(EUI(mac_address))])
    vmi_obj.set_virtual_machine_interface_mac_addresses(
            mac_address_obj)
    vmi_obj.uuid = vmi_id
    vmi_obj.add_virtual_network(vn_obj)
    if security_groups:
        for sg_id in security_groups:
            sg_obj = vnc_api_object.security_group_read(id=sg_id)
            vmi_obj.add_security_group(sg_obj)
    else:
        # Associate default SG
        default_sg_fq_name = project_obj.fq_name[:]
        default_sg_fq_name.append('default')
        sg_obj = vnc_api_object.security_group_read(
            fq_name=default_sg_fq_name)
        vmi_obj.add_security_group(sg_obj)

    vmi_uuid = vnc_api_object.virtual_machine_interface_create(vmi_obj)
    if fixed_ips:
        for fixed_ip in fixed_ips:
            iip_id = str(uuid.uuid4())
            iip_obj = InstanceIp(name=iip_id,
                           subnet_id=fixed_ip['subnet_id'])
            iip_obj.uuid = iip_id
            iip_obj.add_virtual_machine_interface(vmi_obj)
            iip_obj.add_virtual_network(self.vn_obj)
            iip_obj.set_instance_ip_address(fixed_ip['ip_address'])
            vnc_api_object.instance_ip_create(iip_obj)
    else:
        iip_id = str(uuid.uuid4())
        iip_obj = InstanceIp(name=iip_id)
        iip_obj.uuid = iip_id
        iip_obj.add_virtual_machine_interface(vmi_obj)
        iip_obj.add_virtual_network(vn_obj)
        vnc_api_object.instance_ip_create(iip_obj) 
    return vmi_uuid 

def main(args_str = None):
    if not args_str:
       script_args = ' '.join(sys.argv[1:])
    script_args = _parse_args(script_args)
    static_route_sub = script_args.static_route_subnet
    tenant_id = script_args.tenant_id.replace('-', '')
    neutron_obj = neutron_client.Client('2.0', username=script_args.username,
                                 password=script_args.password,
                                 tenant_id=tenant_id,
                                 auth_url=script_args.auth_url,
                                 region_name='RegionOne',
                                 insecure=True)
    vh=VncApi(username='admin',password='contrail123',
               tenant_name='admin',
               api_server_host=script_args.config_node_ip,
               api_server_port='8082')
    project_obj = vh.project_read(id=script_args.tenant_id)
    #net_id=create_network(neutron_obj,script_args.vn_name,[script_args.subnet]) 
    #net_uuid = net_id['network']['id']
    net_uuid = _create_vn(vh,script_args.vn_name,script_args.subnet,project = project_obj)
    #net_uuid ='bc5952b0-097c-4033-aded-4eecf1867e33' 
    vn_obj = vh.virtual_network_read(id=net_uuid)
    vmi_uuid = contrail_create_port(vh,project_obj,script_args.vcenter_vm_mac,vn_obj)
    vmi_obj=vh.virtual_machine_interface_read(id=vmi_uuid)
    #create vm-change the image id accordingly
    print "Creating vm %s with port-id %s"%(vmi_uuid,vmi_uuid)
    cmd ='source /etc/contrail/openstackrc;nova boot --flavor m1.tiny --image 204af559-c75c-4c13-aa42-42d8bc9e61a4 --availability-zone nova  --nic port-id=%s %s '%(vmi_uuid,vmi_uuid)
    if not create_vm(cmd):
        return 
    static_route_subnet = get_static_route_subnet(subnet=static_route_sub)
    rt_table = 'table_' + vmi_uuid
    for route in static_route_subnet:
        routes = [route + '.' +str(i) + '/' + '32' for i in range(1,250)]
        myroutes = ",".join(routes)
#        for elem in routes:
        os.system("python ./provision_static_route.py --prefix %s \
                                                --api_server_ip %s\
                                                --oper add\
                                                --virtual_machine_interface_id %s\
                                                --tenant_name admin\
                                                --user admin\
                                                --password contrail123\
                                                --route_table_name %s"
                                                %(myroutes,script_args.config_node_ip,
                                                 vmi_uuid,rt_table))
        
    

#Usage:python --tenant_id <tenant_id> --config_node_ip <config node ip>
#             --vcenter_vm_mac <vcenter vm mac> --vn_name <name of the vn to be created> --subnet <same subnet as vcenter port group>  
#             --auth_url <auth url:<http://openstack:5000/v2>> 
#python vmi.py  --tenant_id 623939f0f9204f93ac91ba4d0fce9142 
#       --config_node_ip 10.204.216.15 --vcenter_vm_mac 00:50:56:a6:23:79 --vn_name vlan_100 --subnet 11.1.1.0/24 --auth_url http://10.204.216.15:5000/v2

if __name__ == "__main__":
    main()

