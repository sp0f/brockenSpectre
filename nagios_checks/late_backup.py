#!/usr/bin/env python

import boto3
from sys import exit
from datetime import datetime
#from time import time, localtime, strftime, strptime, mktime
#from calendar import timegm

ec2 = boto3.resource('ec2',region_name='eu-west-1')

def getTag(taggedObject, tagKey):
    """get tag defined by tagKey param for collection(ec2.Instance, ec2.Image etc.)"""
    for tag in taggedObject.tags:
        if tag['Key'] == tagKey:
            return tag['Value']
    return None

def getInstancesWithBackupTag(backupTagValue="true"):
    """Find instances that have backup tag set to value of variable backupTagValue (default: backup: true)"""
    #instances = ec2.instances.filter(Filters=[{"Name": "tag:backup", "Values": [backupTagValue]}])
    instances = ec2.instances.filter(Filters=[
        {
        "Name": "tag:backup",
        "Values": [backupTagValue]
        },
        {
            "Name": "instance-state-name",
            "Values": ["running", "stopping", "stopped"]
        }
    ])
    return instances

def getAllInstancesImages():
    """get instance.id list, return all AMI for give instance"""
    images=ec2.images.filter(Filters=[
        {
            'Name': 'tag-key',
            'Values': ["srcInstanceId"]
        }
    ])
    return images


def getLatestCreationDate(image_ids, images_with_creation_date):
    max_creation_date = "1970-01-01T00:00:00.000Z"
    latest_image = ""
    for image_id, creation_date in images_with_creation_date.iteritems():
        if image_id in image_ids:
            if creation_date > max_creation_date:
                max_creation_date=creation_date
                # latest_image=image_id
    if max_creation_date == "1970-01-01T00:00:00.000Z":
        return None
    else:
        # print "latest: "+latest_image+" "+max_creation_date
        return max_creation_date

def main():
    late_in_hours = 25
    scheduled_instances = getInstancesWithBackupTag()

    instance_list = []
    images = getAllInstancesImages()

    # prepare useful dicts
    image_with_instance_id = {}
    image_with_creation_date = {}
    for image in images:
        image_with_instance_id[image.id] = getTag(image,"srcInstanceId")
        image_with_creation_date[image.id] = image.creation_date

    for instance in scheduled_instances:
        instance_images = []

        for image_id, instance_id in image_with_instance_id.iteritems():
            if instance_id == instance.id:
                instance_images.append(image_id)


        instanceName = getTag(instance, 'Name')

        if instanceName == None:
            instanceName = ""

        latest_creation_date=getLatestCreationDate(instance_images,image_with_creation_date)

        if latest_creation_date == None:
            instance_list.append(instance.id + "(" + instanceName + ")")
        else:
            create_time = datetime.strptime(latest_creation_date[:-5], "%Y-%m-%dT%H:%M:%S")
            if (datetime.utcnow()-create_time).total_seconds()/60/60 >late_in_hours:
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
