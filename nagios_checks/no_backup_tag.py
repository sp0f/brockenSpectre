#!/usr/bin/env python

import boto3
from sys import exit

ec2 = boto3.resource('ec2', region_name='eu-west-1')

def findInstancesWithoutBackupTag():
    """Find instances without backup tag"""
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
            return tag['Value']
    return None


def main():
    instance_list = []
    instances = findInstancesWithoutBackupTag()
    for instance in instances:
        instanceName=getTag(instance,'Name')

        if instanceName == None:
            instanceName = ""
        instance_list.append(instance.id + "(" + instanceName + ")")

    # nagios format check output
    if len(instance_list) != 0:
        print "CRITICAL instances without backup tag: "+" ".join(instance_list)+" | "+str(len(instance_list))
        exit(2)
    else:
        print "OK | 0"
        exit(0)

if __name__ == '__main__':
    main()
