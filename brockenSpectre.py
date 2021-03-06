import boto3
import logging
import os, sys
from tagLibraries import *
#from instanceLibraries import *
from imageLibraries import *
import getConfigValue


def main():
    ec2 = boto3.resource('ec2', region_name='eu-west-1')

    # configure and start logging
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', filename=getConfigValue.logFilePath, level=getConfigValue.logLevel)
    #logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=getConfigValue.logLevel)
    #suppress most of boto library logs
    logging.getLogger('botocore').setLevel(getConfigValue.botoLogLevel)
    logging.getLogger('boto3').setLevel(getConfigValue.botoLogLevel)

    # below all the magic happens
    logging.info('Starting backup')

    instances = getInstancesWithBackupTag()
    for instance in instances:
        # backup
        logging.info("Starting backup of %s (%s)",getTag(instance, 'Name'), instance.id)
        ami = createAMI(instance)
        logging.info("Backup created (%s)", ami.id)

        # deregister expired images
        expireThisImages = getExpiredImages(instance)
        expireImages(expireThisImages)

    # deregister abandoned images (images for non existing instances)
    if getConfigValue.deleteAbandoned == True:
        abandoned_images = get_abandoned_images()
        expireImages(abandoned_images)

    logging.info('Backup finished')

if __name__ == '__main__':
    main()
