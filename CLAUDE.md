# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AWS Lambda function designed to clear/delete all objects from an S3 bucket as part of a CodePipeline workflow. The function is triggered by AWS CodePipeline and receives the target bucket name via the pipeline's UserParameters.

**Version**: 2.0 (Refactored with enhanced validation, logging, and observability)

## Architecture

**Entry Point**: `lambda_function.py`
- Simple handler that delegates to the main processing function
- Returns the result of the operation for testability

**Core Logic**: `s3.py`
- `clearS3DeployPipeline(event, context)`: Main function with comprehensive workflow:

  **Validation Phase**:
  1. Validates CodePipeline event structure and extracts job ID
  2. Extracts bucket name from `event["CodePipeline.job"]['data']['actionConfiguration']['configuration']['UserParameters']`
  3. Validates bucket name (not empty, properly formatted)
  4. Verifies bucket existence using `s3.meta.client.head_bucket()`
  5. Handles specific errors: 404 (bucket not found), 403 (permission denied)

  **Execution Phase**:
  6. Counts objects in the bucket using `sum(1 for _ in bucket.objects.all())`
  7. Deletes all objects using `bucket.objects.delete()`
  8. Tracks execution time using `time.time()`

  **Reporting Phase**:
  9. Logs metrics (objects deleted, execution time)
  10. Reports success to CodePipeline via `put_job_success_result(jobId)`
  11. Returns structured response with metrics

**Deployment**:
- No pre-packaged zip file in repository
- Use `zip -r function.zip lambda_function.py s3.py` to create deployment package
- Deploy via AWS CLI, Terraform, CloudFormation, or SAM

## AWS Integration

This Lambda integrates with three AWS services:
- **S3**: Uses boto3 resource interface to list and delete bucket objects, client for validation (`head_bucket`)
- **CodePipeline**: Receives job configuration and reports execution status
- **CloudWatch Logs**: Structured logging using Python's `logging` module

Event structure expects CodePipeline job format with bucket name in:
```
event["CodePipeline.job"]['data']['actionConfiguration']['configuration']['UserParameters']
```

## Logging and Observability

**Logging Strategy**:
- Uses Python's `logging` module (not `print()`)
- Log level: INFO for normal operations, ERROR for failures
- All logs include contextual information (bucket name, object count, timing)
- Stack traces included for exceptions via `exc_info=True`

**Metrics Tracked**:
- Number of objects in bucket before deletion
- Total objects deleted
- Execution time in seconds
- Structured return value with `statusCode`, `bucket`, `objects_deleted`, `execution_time`

**Log Examples**:
```
[INFO] Evento recebido do CodePipeline
[INFO] Iniciando limpeza do bucket: my-bucket
[INFO] Bucket 'my-bucket' existe e é acessível
[INFO] Total de objetos a deletar: 150
[INFO] Deletados 150 objetos do bucket 'my-bucket'
[INFO] Limpeza concluída com sucesso em 2.35 segundos
```

## Error Handling

Comprehensive error handling with three levels:

1. **`ValueError`**: Validation errors
   - Malformed CodePipeline event structure
   - Missing or empty bucket name
   - Bucket not found (404)
   - Permission denied (403)

2. **`ClientError` (boto3)**: AWS SDK errors
   - Extracts error code and message from response
   - Reports to CodePipeline with structured error details

3. **Generic `Exception`**: Unexpected errors
   - Catches any unforeseen issues
   - Logs full stack trace
   - Reports to CodePipeline with error message

All error paths:
- Log the error with `logger.error()`
- Call `put_job_failure_result(jobId, failureDetails)`
- Return structured error response (`statusCode: 500`, `error: message`)

## IAM Permissions Required

The Lambda execution role needs:

**S3 Permissions**:
- `s3:ListBucket` - Count objects before deletion
- `s3:DeleteObject` - Delete objects from bucket
- `s3:HeadBucket` - Validate bucket existence (added in v2.0)

**CodePipeline Permissions**:
- `codepipeline:PutJobSuccessResult` - Report success
- `codepipeline:PutJobFailureResult` - Report failure

**CloudWatch Logs Permissions**:
- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

## Best Practices Implemented

✅ **No global clients**: `codepipeline_client` created inside function to avoid connection reuse issues
✅ **Structured logging**: Uses `logging` module with appropriate levels
✅ **Input validation**: Checks event structure, bucket name, and bucket existence before operations
✅ **Metrics tracking**: Counts objects and measures execution time
✅ **Error messages**: Serializable, descriptive error messages for CodePipeline
✅ **Testability**: Function returns structured response for easier unit testing
✅ **Security**: Validates bucket exists and checks permissions before destructive operations

## Code Style

- Python 3.x compatible
- Consistent 4-space indentation
- Descriptive variable names
- Comprehensive comments for each phase
- Uses f-strings for string formatting
- boto3 resource interface for S3 operations (simpler than client for bulk operations)
