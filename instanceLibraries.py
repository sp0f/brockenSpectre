import boto3
import logging
ec2 = boto3.resource('ec2')


# find running instances
def findRunningInstances():
    "return collection containing all running instances"
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
