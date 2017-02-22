import boto3
import logging

ec2 = boto3.resource('ec2')

# find instances without backup tag
def findInstancesWithoutBackupTag():
    """"DEPRECATED - need to be upgraded. Find instances without backup tag"""
    instances = ec2.instances.all()

    instancesList = []  # list of instances without backup tag
    for instance in instances:
        backupTag = False
        for tag in instance.tags:
            if tag['Key'] == 'backup':
                backupTag = True
        if backupTag == False:
            instancesList.append(instance)
    return instancesList

def getTag(taggedObject, tagKey):
    """get tag defined by tagKey param for collection(ec2.Instance, ec2.Image etc.)"""
    for tag in taggedObject.tags:
        if tag['Key'] == tagKey:
            logging.debug("Found tag %s with value %s",tagKey,tag['Value'])
            return tag['Value']
    logging.warn("Tag %s not found",tagKey)
    return None

def getInstancesByName(instanceName):
    """return one or more instances (ec2.instancesCollection) with Name tag defined as instanceName"""
    instances=ec2.instances.filter(Filters=[
        {
            "Name": "tag:Name",
            "Values": [instanceName]
        }
    ])
    return instances

# find instances with backup tag set to true
# TODO make it case insensitive
def getInstancesWithBackupTag(backupTagValue="true"):
    """Find instances that have backup tag set to value of variable backupTagValue (default: backup: true)"""

    instances = ec2.instances.filter(Filters=[{"Name": "tag:backup", "Values": [backupTagValue]}])
    for instance in instances:
        instanceName=getTag(instance,"Name")
        logging.info("Found instance %s (%s) with 'backup' tag set to '%s'",instanceName,instance.id,backupTagValue)
    return instances
