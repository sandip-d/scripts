import os
import sys
import argparse
from vnc_api.vnc_api import  *
from neutronclient.neutron import client as neutron_client
import uuid
import netaddr
from netaddr import EUI

def _parse_args( args_str):
    parser = argparse.ArgumentParser()
    args, remaining_argv = parser.parse_known_args(args_str.split())
    parser.add_argument(
                "--name", nargs='+', help="Name of the logical interface in the same order as physical interface id ",required=True)
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
                "--vcenter_vm_mac",  help="Mac address of vcenter vm ",required=True)
    parser.add_argument(
                "--vn_name", help="Vn name to launch vmi",required=True)
    parser.add_argument(
                "--subnet", help="subnet of the vn",required=True)
    parser.add_argument(
                "--vlan",  help="vlan of the vcnetr port group",required=True)
    parser.add_argument(
                "--auth_url", nargs='?', default="check_string_for_empty",help="Auth Url",required=True)
    args = parser.parse_args(remaining_argv)
    return args

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
        return none

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
    
    for interface in script_args.physical_interfaces_id:
        pif_obj = vh.physical_interface_read(id=interface)
        name = script_args.name.pop(0)
        lif_obj = LogicalInterface(name=name,
                                   parent_obj=pif_obj,
                                   display_name=name)

        lif_obj.set_logical_interface_vlan_tag(int(script_args.vlan))
        lif_uuid = vh.logical_interface_create(lif_obj)
        lif_obj = vh.logical_interface_read(id=lif_uuid)

        lif_obj.add_virtual_machine_interface(vmi_obj)
        vh.logical_interface_update(lif_obj)


#Usage:python --name <list of logical inetrface name> --physical_interfaces_id <list of physical interfaces id> --tenant_id <tenant_id> --config_node_ip <config node ip>
#             --vcenter_vm_mac <vcenter vm mac> --vn_name <name of the vn to be created> --subnet <same subnet as vcenter port group> --vlan <vlan of the vcenter port group> 
#             --auth_url <auth url:<http://openstack:5000/v2>> 
#python lif.py --name p6p1.100 p514p2.100 --physical_interfaces_id 21fc448f-c17e-4efa-9385-bc0e5c1b9e68 c9dc3569-74b5-4f2e-9820-17d07c52f543 --tenant_id 623939f0f9204f93ac91ba4d0fce9142 
#       --config_node_ip 10.204.216.15 --vcenter_vm_mac 00:50:56:a6:23:79 --vn_name vlan_100 --subnet 11.1.1.0/24 --vlan 100 --auth_url http://10.204.216.15:5000/v2

if __name__ == "__main__":
    main()
