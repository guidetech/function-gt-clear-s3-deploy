import boto3
import logging
import time

from botocore.exceptions import ClientError

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def clearS3DeployPipeline(event, context):
    start_time = time.time()
    codepipeline_client = boto3.client('codepipeline')

    try:
        logger.info("Evento recebido do CodePipeline", extra={"event": event})

        # Validar estrutura do evento
        if "CodePipeline.job" not in event:
            raise ValueError("Evento inválido: campo 'CodePipeline.job' não encontrado")

        job_id = event['CodePipeline.job'].get('id')
        if not job_id:
            raise ValueError("Evento inválido: 'job id' não encontrado")

        # Extrair nome do bucket
        try:
            bucketname = event["CodePipeline.job"]['data']['actionConfiguration']['configuration']['UserParameters']
        except KeyError as e:
            raise ValueError(f"Evento inválido: não foi possível extrair UserParameters - {str(e)}")

        # Validar nome do bucket
        if not bucketname or not bucketname.strip():
            raise ValueError("Nome do bucket está vazio")

        bucketname = bucketname.strip()
        logger.info(f"Iniciando limpeza do bucket: {bucketname}")

        # Inicializar cliente S3
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucketname)

        # Validar se o bucket existe
        try:
            s3.meta.client.head_bucket(Bucket=bucketname)
            logger.info(f"Bucket '{bucketname}' existe e é acessível")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise ValueError(f"Bucket '{bucketname}' não existe")
            elif error_code == '403':
                raise ValueError(f"Sem permissão para acessar o bucket '{bucketname}'")
            else:
                raise

        # Contar objetos antes da deleção
        object_count = sum(1 for _ in bucket.objects.all())
        logger.info(f"Total de objetos a deletar: {object_count}")

        # Deletar todos os objetos
        if object_count > 0:
            bucket.objects.delete()
            logger.info(f"Deletados {object_count} objetos do bucket '{bucketname}'")
        else:
            logger.info(f"Bucket '{bucketname}' já está vazio")

        # Calcular tempo de execução
        execution_time = time.time() - start_time
        logger.info(f"Limpeza concluída com sucesso em {execution_time:.2f} segundos")

        # Reportar sucesso ao CodePipeline
        codepipeline_client.put_job_success_result(jobId=job_id)

        return {
            'statusCode': 200,
            'bucket': bucketname,
            'objects_deleted': object_count,
            'execution_time': execution_time
        }

    except ClientError as e:
        error_message = f"Erro do AWS SDK: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        logger.error(error_message, exc_info=True)

        codepipeline_client.put_job_failure_result(
            jobId=event.get('CodePipeline.job', {}).get('id', 'unknown'),
            failureDetails={
                'type': 'JobFailed',
                'message': error_message
            })

        return {
            'statusCode': 500,
            'error': error_message
        }

    except Exception as e:
        error_message = f"Erro inesperado: {str(e)}"
        logger.error(error_message, exc_info=True)

        codepipeline_client.put_job_failure_result(
            jobId=event.get('CodePipeline.job', {}).get('id', 'unknown'),
            failureDetails={
                'type': 'JobFailed',
                'message': error_message
            })

        return {
            'statusCode': 500,
            'error': error_message
        }