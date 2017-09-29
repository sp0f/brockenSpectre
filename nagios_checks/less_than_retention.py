#!/usr/bin/env python

import boto3
from sys import exit
import datetime

ec2 = boto3.resource('ec2')

def getInstancesWithBackupTag(backupTagValue="true"):
    """Find instances that have backup tag set to value of variable backupTagValue (default: backup: true)"""

    instances = ec2.instances.filter(Filters=[{"Name": "tag:backup", "Values": [backupTagValue]}])
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

def getTag(taggedObject, tagKey):
    """get tag defined by tagKey param for collection(ec2.Instance, ec2.Image etc.)"""
    for tag in taggedObject.tags:
        if tag['Key'] == tagKey:
            return tag['Value']
    return None
def getInstacneCreateTime(instance):
    #print instance.id
    if instance.state['Code'] != 48: # if instance is not in Terminated state
        rootVolumeId=list(instance.volumes.filter(Filters=[{'Name': 'attachment.device', 'Values':["/dev/sda1","/dev/xvda"]}]))[0].id
        return ec2.Volume(rootVolumeId).create_time
    else:
        return None

def main():
    instance_list = []
    new_instance_list = []
    image_with_instance_id = {}
    scheduled_instances = getInstancesWithBackupTag()
    images = getAllInstancesImages()

    # prepare useful dict
    for image in images:
        image_with_instance_id[image.id] = getTag(image, "srcInstanceId")

    for instance in scheduled_instances:
        instanceName = getTag(instance, 'Name')
        if instanceName == None:
            instanceName = ""
        retention=getTag(instance,'retention')
        if retention == None:
            retention = 7
        else:
            retention = int(retention)
        number_of_images = 0
        for image_id, backuped_instance_id in image_with_instance_id.iteritems():
            if backuped_instance_id == instance.id:
                number_of_images += 1
        if number_of_images < retention:
            # no alerts for newly created instances
            createTime=getInstacneCreateTime(instance)
            if createTime is not None: # instance were terminated
                if (datetime.datetime.now().replace(tzinfo=None) - createTime.replace(tzinfo=None) < datetime.timedelta(days=retention)):
                    #print "New instance: "+instanceName+"created: "+str(createTime)
                    new_instance_list.append(instanceName+"("+str(createTime)+")")
                    continue
                else:
                    instance_list.append(instance.id + "(" + instanceName + ") " + str(number_of_images) + "/" + str(retention))

    # nagios format check output
    if len(instance_list) != 0:
        print "CRITICAL backup retention problem for instance(s): " + ", ".join(instance_list) + " | " + str(len(instance_list))
        exit(2)
    else:
        additional_info="new(unchecked) instances: "+", ".join(new_instance_list)
        print "OK: "+additional_info+" | 0"
        exit(0)
if __name__ == '__main__':
    main()