### AWS EC2 instance backup using AMI (pyton/boto3)

#### Alpha ALERT !
This is totaly work in progress ... not suitable for usage jet

#### How does it work

Start it from cron and hope for the best :)

##### Workflow
1. get all instances with tag `backup` set to `true`
2. for each of above instance
  1. create AMI
  2. tag AMI with tags needed for recovery (ip, subnet, name ...)
  3. check instance `retention` tag
  4. if there is a AMI that is older then number of days defined by `retention` and number of backups (AMIs) for this instance is grater than `retntion`
    1. expire it
    2. delete all snapshots belonging to this AMI

##### Used tags
###### Instance
* `backup` (`true |  false`) - if set to `true` instance will be backuped
* `retention` - define backup retention. If not set `retention` from config file will be used

###### AMI
* `Name` - ami name in format `BACKUP `+`instance_name`+`date`
* `created` - in `time()` format (epoch)
* `srcInstanceId` - source instance id
* `srcInstanceName` - source instance `Name` tag
* `srcPrimaryIP` - source instance primary IP (for now)
* `srcSubnetId` - source instance subnet id
* `srcSecurityGroupId` - source instance first (for now) security group
* `srcInstanceType` - source instance type (m4.large, t2.medium, ...)


#### sample config file (config.yaml)

```
defaults:
  retention: 7
  log file path: "./brokenSpectre.log"
  # [10,20,30,40,50]... higher number, less logs (https://docs.python.org/2/library/logging.html#logging-levels)
  log level: 10
  boto log level: 50
aws account id: "1234567890"
```