import boto3
from sys import exit

ec2 = boto3.resource('ec2')

def getInstancesWithBackupTag(backupTagValue="true"):
    """Find instances that have backup tag set to value of variable backupTagValue (default: backup: true)"""

    instances = ec2.instances.filter(Filters=[{"Name": "tag:backup", "Values": [backupTagValue]}])
    return instances

def getAllInstanceImages(instanceId):
    """return all AMI for give instance"""
    images=ec2.images.filter(Filters=[
        {
            'Name': 'tag:srcInstanceId',
            'Values': [instanceId]
        }
    ])

    return images

def getTag(taggedObject, tagKey):
    """get tag defined by tagKey param for collection(ec2.Instance, ec2.Image etc.)"""
    for tag in taggedObject.tags:
        if tag['Key'] == tagKey:
            return tag['Value']
    return None

def main():
    scheduled_instances = getInstancesWithBackupTag()

    instance_list = []
    for instance in scheduled_instances:

        instanceName = getTag(instance, 'Name')
        if instanceName == None:
            instanceName = ""

        retention=getTag(instance,'retention')
        if retention == None:
            retention = 7
        else:
            retention = int(retention)

        number_of_images = len(list(getAllInstanceImages(instance.id)))

        if number_of_images < retention:
            instance_list.append(instance.id + "(" + instanceName + ") " + str(number_of_images) + "/" + str(retention))

    # nagios format check output
    if len(instance_list) != 0:
        print "CRITICAL backup retention problem for instance(s): " + ", ".join(instance_list) + " | " + str(len(instance_list))
        exit(2)
    else:
        print "OK | 0"
        exit(0)
if __name__ == '__main__':
    main()