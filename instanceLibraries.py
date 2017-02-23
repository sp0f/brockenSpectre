import boto3
import logging
ec2 = boto3.resource('ec2')


# find running instances
def findRunningInstances():
    """return collection containing all running instances"""
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    for instance in instances:
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                instanceName = tag['Value']
        print(str(instanceName) + "," + str(instance.id))
    return instances

def getFirstPrimaryIP(instance):
    """return first primary IP address of first network interface"""
    addresses = instance.network_interfaces_attribute[0]['PrivateIpAddresses']
    for address in addresses:
        if address['Primary'] == True:
            logging.debug("Found primary IP address (%s) for instance %s", address['PrivateIpAddress'], instance.id)
            return address['PrivateIpAddress']
    logging.warning("Can't found primary IP address for instance %s",instance.id)
    return None

def getBasicNetworkConfig(instance):
    """get primary IP address of firest network interface and its subnet
    return: securityGroupId, subnetId, primaryIp"""
    network = instance.network_interfaces_attribute[0]
    subnetId=network['SubnetId']
    securityGroupId=network['Groups'][0]['GroupId']
    for address in network['PrivateIpAddresses']:
        if address['Primary'] == True:
            logging.debug("Found primary IP address (%s) for instance %s", address['PrivateIpAddress'], instance.id)
            primaryIp=address['PrivateIpAddress']
    return securityGroupId, subnetId, primaryIp
