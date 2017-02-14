import boto3
import logging
from re import sub
from tagLibraries import getTag
from time import time, localtime, strftime

ec2 = boto3.resource('ec2')

def getAllInstanceImages(instance):
    """return all AMI for give instance"""
    #TODO remove owner-id (at all or to config file)
    logging.debug("Start searching for images of instance %s",instance.id)
    images=ec2.images.filter(Filters=[
        {
            'Name': 'owner-id',
            'Values': ['260187409195']
        },
        {
            'Name': 'tag:fromInstance',
            'Values': [instance.id]
        }
    ])
    # only in DEBUG mode
    if (logging.getLogger().getEffectiveLevel() <= 10):
        if images == None:
            logging.debug("Can't find any images for instance %s",instance.id)
        else:
            for image in images:
                logging.debug("Found image %s for instance %s",image.id, instance.id)
    return images

def getExpiredImages(instance):
    """return list of expired images based on:
        * image created tag
        * instance retention tag
        * expirationPeriodInDays variable (default: 7)

        Image will be expired only if created date is older than expirationPeriodInDays and number of images is grater than
        instance retention tag value.

        If there arent any images to be expired it will return None
    """
    expiredImageList=[]

    images = getAllInstanceImages(instance)

    retention = getTag(instance,"retention")
    if retention == None:
        logging.warning("Retention tag for instance %s not set, assume default",instance.id)
        retention = 7
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
    "create ami for a instance and tag it with needed tags"
    instanceName=getTag(instance,'Name')
    if instanceName == None: # if no Name tag found, use instance id instead
        instanceName=instance.id
    # create ami name compliant with AWS AMI name standard:
    # Constraints: 3-128 alphanumeric characters, parentheses (()), square brackets ([]), spaces ( ), periods (.),
    # slashes (/), dashes (-), single quotes ('), at-signs (@), or underscores(_)
    amiShortName="BACKUP-"+sub('[^A-Za-z0-9]+', '',instanceName[0:90])+"-"+strftime("%d%m%Y-%H%M%S(%Z)",localtime())
    ami=instance.create_image(
        Name=amiShortName,
        Description="BACKUP "+instanceName+"["+instance.id+"] "+strftime("%d.%m.%Y-%H:%M:%S (%Z)",localtime()),
        NoReboot=True
    )
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
                'Key': 'fromInstance',
                'Value': instance.id
            }
        ]
    )
    return ami

def expireImages(images):
    if images != None:
        for image in images:
            logging.info("Deregistering image %s",image.id)
            image.deregister()
