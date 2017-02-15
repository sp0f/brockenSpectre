AWS EC2 instance backup using AMI (pyton/boto3)

sample config file (yaml)

defaults:
  retention: 7
  log file path: "./brokenSpectre.log"
  # [10,20,30,40,50]... higher number, less logs (https://docs.python.org/2/library/logging.html#logging-levels)
  log level: 10
  boto log level: 50
aws account id: "260187409195"