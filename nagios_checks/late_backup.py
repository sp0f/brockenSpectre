#!/usr/bin/env python

import boto3
from sys import exit
from time import time, localtime, strftime, strptime, mktime
from calendar import timegm

ec2 = boto3.resource('ec2')

def getTag(taggedObject, tagKey):
    """get tag defined by tagKey param for collection(ec2.Instance, ec2.Image etc.)"""
    for tag in taggedObject.tags:
        if tag['Key'] == tagKey:
            return tag['Value']
    return None

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


def getNewestInstanceImage(instanceId):
    """return newest image ID for instance"""
    images = getAllInstanceImages(instanceId)
    images=sorted(images, key=lambda image: mktime(strptime(image.creation_date[:-5], "%Y-%m-%dT%H:%M:%S")), reverse=True)

    if len(list(images)) == 0:
        return None
    return images[0]

def main():
    late_in_hours=24
    scheduled_instances=getInstancesWithBackupTag()

    instance_list=[]
    for instance in scheduled_instances:
        instanceName = getTag(instance, 'Name')

        if instanceName == None:
            instanceName = ""

        image=getNewestInstanceImage(instance.id)
        if image == None:
            instance_list.append(instance.id + "(" + instanceName + ")")
        else:
            create_time = mktime(strptime(image.creation_date[:-5], "%Y-%m-%dT%H:%M:%S"))
            if timegm(localtime()) - create_time > (60*60*late_in_hours):
                instance_list.append(instance.id + "(" + instanceName + ")")

    # nagios format check output
    if len(instance_list) != 0:
        print "CRITICAL no backup (last " + str(late_in_hours) +"h) for instance(s): " + " ".join(instance_list) + " | " + str(len(instance_list))
        exit(2)
    else:
        print "OK | 0"
        exit(0)

if __name__ == '__main__':
    main()
