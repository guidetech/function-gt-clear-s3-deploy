from s3 import clearS3DeployPipeline

def lambda_handler(event, context):
    clearS3DeployPipeline(event, context)