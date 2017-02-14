import boto3
ec2 = boto3.resource('ec2')


# find running instances
def findRunningInstances():
    "return collection containing all running instances"
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    for instance in instances:
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                instanceName = tag['Value']
        print(str(instanceName) + "," + str(instance.id))
    return instances
