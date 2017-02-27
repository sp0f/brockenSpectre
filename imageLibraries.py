import boto3
import logging
from re import sub
from tagLibraries import getTag
from instanceLibraries import getBasicNetworkConfig
from time import time, localtime, strftime, strptime, mktime
import getConfigValue

ec2 = boto3.resource('ec2')


def getAllInstanceImages(instanceId):
    """return all AMI for give instance"""
    logging.debug("Start searching for images of instance %s",instanceId)
    images=ec2.images.filter(Filters=[
        {
            'Name': 'owner-id',
            'Values': [getConfigValue.ownerId]
        },
        {
            'Name': 'tag:srcInstanceId',
            'Values': [instanceId]
        }
    ])
    # only in DEBUG mode
    if (logging.getLogger().getEffectiveLevel() <= 10):
        if images == None:
            logging.debug("Can't find any images for instance %s",instanceId)
        else:
            for image in images:
                logging.debug("Found image %s for instance %s",image.id, instanceId)
    return images

def getAllBackupedInstancesIds():
    """return list of all instances id that were backuped by this tool"""
    images = ec2.images.filter(Filters=[
        {
            'Name': 'owner-id',
            'Values': [getConfigValue.ownerId]
        },
        {
            'Name': 'tag-key',
            'Values': ["srcInstanceId"]
        }
    ])

    backupedInstances=[]
    for image in images:
       srcInstanceId=getTag(image,"srcInstanceId")
       if srcInstanceId not in backupedInstances:
           backupedInstances.append(srcInstanceId)

    return backupedInstances

def getNewestInstanceImage(instanceId):
    """return newest image ID for instance"""
    images = getAllInstanceImages(instanceId)
    if images == None:
        logging.critical("Can't find any images for instance %s", instanceId)

    images=sorted(images, key=lambda image: mktime(strptime(image.creation_date[:-5], "%Y-%m-%dT%H:%M:%S")), reverse=True)
    logging.info("Newest image id %s", images[0].id)

    return images[0]


def getExpiredImages(instance):
    """return list of expired images based on:
        * image created tag
        * instance retention tag

        Image will be expired only if created date is older than retention and number of images is grater than
        instance retention tag value.

        If there aren't any images to be expired it will return None
    """
    expiredImageList=[]

    images = getAllInstanceImages(instance.id)

    retention = getTag(instance,"retention")
    if retention == None:
        logging.warning("Retention tag for instance %s not set, assume default",instance.id)
        retention = getConfigValue.retention
    else:
        retention=float(retention)
        logging.info("Retention for instance %s set to %s",instance.id,str(retention))

    numberOfImages = len(list(images)) # dirty method to get number of elements in boto3 collection

    # need at least number of copies defined by retention
    if numberOfImages <= retention:
        logging.warning("Number of existing backup images (%s) is less of equal than retention %s. Nothing will be expired.",str(numberOfImages),str(retention))
        return None

    for image in images:
        created=float(getTag(image,'created'))
        if time()-created > (60*60*24*retention):
            logging.info("%s is older than %s day(s) and will be deregistered", image.id,str(retention))
            expiredImageList.append(image)
        else:
            logging.debug("%s if younger than %s day(s), will not be deregistered",image.id,str(retention))

    return expiredImageList

def createAMI(instance):
    """create ami for a instance and tag it with needed tags"""
    instanceName=getTag(instance,'Name')
    if instanceName == None: # if no Name tag found, use instance id instead
        instanceName=instance.id
    # create ami name compliant with AWS AMI name standard:
    # Constraints: 3-128 alphanumeric characters, parentheses (()), square brackets ([]), spaces ( ), periods (.),
    # slashes (/), dashes (-), single quotes ('), at-signs (@), or underscores(_)
    amiShortName="BACKUP-"+sub('[^A-Za-z0-9,\-, ,\(,\),\[,\],\.,\/,\',@,_]+', '',instanceName[0:90])+"-"+strftime("%d%m%Y-%H%M%S(%Z)",localtime())
    ami=instance.create_image(
        Name=amiShortName,
        Description="BACKUP "+instanceName+"["+instance.id+"] "+strftime("%d.%m.%Y-%H:%M:%S (%Z)",localtime()),
        NoReboot=True
    )
    securityGroupId, subnetId, primaryIp = getBasicNetworkConfig(instance)
    ami.create_tags(
        Tags=[
            {
                'Key': 'Name',
                'Value': amiShortName
            },
            {
                'Key': 'created',
                'Value': str(time())
            },
            {
                'Key': 'srcInstanceId',
                'Value': instance.id
            },
            {
                'Key': 'srcInstanceName',
                'Value': instanceName
            },
            {
                'Key': 'srcPrimaryIP',
                'Value': primaryIp
            },
            {
                'Key': 'srcSubnetId',
                'Value': subnetId
            },
            {
                'Key': 'srcSecurityGroupId',
                'Value': securityGroupId
            },
            {
                'Key': 'srcInstanceType',
                'Value': instance.instance_type
            }
        ]
    )
    return ami

def expireImages(images):
    """expire ami"""
    if images != None:
        for image in images:
            logging.info("Deregistering image %s",image.id)
            image.deregister()
            deleteExpiredSnapshots(image.id)


def deleteExpiredSnapshots(imageId):
    """delete snapshots created for deregistered ami"""
    snapshots = ec2.snapshots.filter(Filters=[
        {
            'Name': 'description',
            'Values': ["Created by CreateImage* for "+imageId+" *"]
        }
    ])

    for snapshot in snapshots:
        logging.info("Cleanup snapshot %s for image %s", snapshot.id, imageId)
        snapshot.delete()
