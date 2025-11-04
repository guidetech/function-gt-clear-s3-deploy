import boto3

from botocore.exceptions import ClientError

codepipeline_client = boto3.client('codepipeline')
 
 
def clearS3DeployPipeline(event, context):
   try:
       
       print(event)
       s3 = boto3.resource("s3")
       bucketname = event["CodePipeline.job"]['data']['actionConfiguration']['configuration']['UserParameters']
       print(bucketname)
       
       bucket = s3.Bucket(bucketname)
       bucket.objects.delete()
 
       codepipeline_client.put_job_success_result(jobId=event['CodePipeline.job']['id'])
   except ClientError as e:
       print("Boto3 exception", e)
       codepipeline_client.put_job_failure_result(
           jobId=event['CodePipeline.job']['id'],
           failureDetails={
               'type': 'JobFailed',
               'message': e.response
           })
   except Exception as e:
       print("Error", e)
       codepipeline_client.put_job_failure_result(
           jobId=event['CodePipeline.job']['id'],
           failureDetails={
               'type': 'JobFailed',
               'message': e.args
           })