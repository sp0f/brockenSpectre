import boto3
import logging
from tagLibraries import *
#from instanceLibraries import *
from imageLibraries import *

# configuration
# TODO move it to config file or cmd line argument
logFilePath="brokenSpectre.log"
botoLogLevel=logging.CRITICAL

def main():
    ec2 = boto3.resource('ec2')

    # configure and start logging
    #logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', filename=logFilePath, level=logging.INFO)
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.DEBUG)
    #suppress most of boto library logs
    logging.getLogger('botocore').setLevel(botoLogLevel)
    logging.getLogger('boto3').setLevel(botoLogLevel)

    # below all the magic happens
    logging.info('Starting backup')

    instances=getInstancesWithBackupTag()
    for instance in instances:
        # backup
        logging.info("Starting backup of %s (%s)",getTag(instance,'Name'),instance.id)
        ami=createAMI(instance)
        logging.info("Backup created (%s)",ami.id)

        # deregister expired images
        expireThisImages=getExpiredImages(instance)
        expireImages(expireThisImages)
    logging.info('Backup finished')

def mainTest():
    ec2 = boto3.resource('ec2')
    instance=ec2.Instance('i-0990673e61fc85a7a')
    securityGroupId, subnetId, primaryIp = getBasicNetworkConfig(instance)
    print(securityGroupId,subnetId,primaryIp)
if __name__ == '__main__':
    mainTest()
