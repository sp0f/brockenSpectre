import boto3
import botocore
import logging
from re import sub
from tagLibraries import getTag
from instanceLibraries import getBasicNetworkConfig
from time import time, localtime, strftime, strptime, mktime, sleep
import getConfigValue

ec2 = boto3.resource('ec2', region_name='eu-west-1')
ec2_client = boto3.client('ec2', region_name='eu-west-1')


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

def get_abandoned_images():
    backuped_instance_ids=getAllBackupedInstancesIds()
    abandoned_images = []
    for instance_id in backuped_instance_ids:
        if instance_exists(instance_id) == False:
            logging.warning("Fond images for non existing instance %s", instance_id)
            abandoned_images.extend(list(getAllInstanceImages(instance_id)))
    # only in DEBUG mode
    if (logging.getLogger().getEffectiveLevel() <= 10):
        for image in abandoned_images:
            name=getTag(image, 'Name')
            created=getTag(image, 'created')
            logging.debug("Abandoned image %s %s %s", image.id, name, created)
    return abandoned_images


def instance_exists(instance_id):
    """check if instance exists, return True or False"""
    instance = ec2.Instance(instance_id)
    try:
        instance.load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "InvalidInstanceID.NotFound":
            return False
        else:
            raise
    else:
        return True

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
        logging.info("Retention tag for instance %s not set, assume default",instance.id)
        retention = getConfigValue.retention
    else:
        retention=float(retention)
        logging.info("Retention for instance %s set to %s",instance.id,str(retention))

    numberOfImages = len(list(images)) # dirty method to get number of elements in boto3 collection

    # need at least number of copies defined by retention
    if numberOfImages <= retention:
        logging.info("Number of existing backup images (%s) is less of equal than retention %s. Nothing will be expired.",str(numberOfImages),str(retention))
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
    logging.info("Waiting until image exists %s to ", ami.id)
    try:
        ami.wait_until_exists();
    # waiter = ec2_client.get_waiter('image_available')
    # try:
    #     waiter.wait(
    #         ImageIds=[
    #             ami.id
    #         ],
    #         WaiterConfig={
    #             'Delay': 45,
    #             'MaxAttempts': 40
    #         }
    #     )
    except botocore.exceptions.WaiterError:
        print("[!] Creating AMI "+ami.id+" is taking to long. Will try to tag an continue")

    try:
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
                    # TODO it should be a list ...
                    'Key': 'srcSecurityGroupId',
                    'Value': securityGroupId
                },
                {
                    'Key': 'srcInstanceType',
                    'Value': instance.instance_type
                },
                {
                    'Key': 'boundryProtected',
                    'Value': 'true'
                }
            ]
        )
    except:
        print("[!] Faild to tag AMI "+ami.id+". Will try to wait for image to become available.")
        ami.wait_until_exists(Filters=[{'Name': 'state', 'Values': ['available']}]);
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
                    # TODO it should be a list ...
                    'Key': 'srcSecurityGroupId',
                    'Value': securityGroupId
                },
                {
                    'Key': 'srcInstanceType',
                    'Value': instance.instance_type
                },
                {
                    'Key': 'boundryProtected',
                    'Value': 'true'
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
            while len(ec2_client.describe_images(ImageIds=[image.id])['Images']) > 0:
                sleep(5)
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
