from yaml import load


def getYAMLConfig(configFile):
    with open(configFile,"r") as file:
        configDataRaw=file.read()
    configDataYAML=load(configDataRaw)
    return configDataYAML

# configuration
configDataYAML = getYAMLConfig("config.yaml")  # TODO move to cmd line option -c

retention = configDataYAML["defaults"]["retention"]
ownerId = configDataYAML["aws account id"]
logFilePath = configDataYAML["defaults"]["log file path"]
logLevel = configDataYAML["defaults"]["log level"]
botoLogLevel = configDataYAML["defaults"]["boto log level"]
deleteAbandoned = configDataYAML["defaults"]["delete abandoned"]
