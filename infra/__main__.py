import os

import pulumi
import pulumi_azure_native as azure
from pulumi_azure_native import compute, network, resources

config = pulumi.Config()
admin_username = config.get("adminUsername") or os.environ.get("USER", "azureuser")
admin_public_key = config.require("adminPublicKey")
location = config.get("location") or "eastus"
vm_size = config.get("vmSize") or "Standard_B2ms"

resource_group = resources.ResourceGroup(
    "rg-coding",
    resource_group_name="rg-coding-vm",
    location=location,
)

vnet = network.VirtualNetwork(
    "vnet",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    address_space=network.AddressSpaceArgs(address_prefixes=["10.0.0.0/16"]),
)

subnet = network.Subnet(
    "subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24",
)

public_ip = network.PublicIPAddress(
    "pip",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    public_ip_allocation_method="Static",
    public_ip_address_version="IPv4",
    sku=network.PublicIPAddressSkuArgs(name="Standard", tier="Regional"),
)

nsg = network.NetworkSecurityGroup(
    "nsg",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    security_rules=[
        network.SecurityRuleArgs(
            name="SSH",
            protocol="Tcp",
            source_port_range="*",
            destination_port_range="22",
            source_address_prefix="*",
            destination_address_prefix="*",
            access="Allow",
            priority=100,
            direction="Inbound",
        ),
    ],
)

nic = network.NetworkInterface(
    "nic",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    ip_configurations=[
        network.NetworkInterfaceIPConfigurationArgs(
            name="ipconfig1",
            subnet=network.SubnetArgs(id=subnet.id),
            private_ip_allocation_method="Dynamic",
            public_ip_address=network.PublicIPAddressArgs(id=public_ip.id),
        ),
    ],
    network_security_group=network.NetworkSecurityGroupArgs(id=nsg.id),
)

vm = compute.VirtualMachine(
    "codingvm",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    hardware_profile=compute.HardwareProfileArgs(vm_size=vm_size),
    os_profile=compute.OSProfileArgs(
        computer_name="codingvm",
        admin_username=admin_username,
        linux_configuration=compute.LinuxConfigurationArgs(
            disable_password_authentication=True,
            ssh=compute.SshConfigurationArgs(
                public_keys=[
                    compute.SshPublicKeyArgs(
                        path=f"/home/{admin_username}/.ssh/authorized_keys",
                        key_data=admin_public_key,
                    ),
                ],
            ),
        ),
    ),
    storage_profile=compute.StorageProfileArgs(
        image_reference=compute.ImageReferenceArgs(
            publisher="Canonical",
            offer="0001-com-ubuntu-server-jammy",
            sku="22_04-lts-gen2",
            version="latest",
        ),
        os_disk=compute.OSDiskArgs(
            create_option="FromImage",
            managed_disk=compute.ManagedDiskParametersArgs(
                storage_account_type="StandardSSD_LRS",
            ),
        ),
    ),
    network_profile=compute.NetworkProfileArgs(
        network_interfaces=[
            compute.NetworkInterfaceReferenceArgs(id=nic.id, primary=True),
        ],
    ),
)

pulumi.export("resourceGroupName", resource_group.name)
pulumi.export("vmName", vm.name)
pulumi.export("vmSize", vm.hardware_profile.vm_size)
pulumi.export("publicIp", public_ip.ip_address)
