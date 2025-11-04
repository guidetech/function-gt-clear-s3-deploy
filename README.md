# Lambda Function: Clear S3 Deploy

AWS Lambda function que limpa (deleta todos os objetos) de um bucket S3 como parte de um workflow do AWS CodePipeline.

## Descrição

Esta função é executada como uma ação customizada no CodePipeline e remove todos os objetos de um bucket S3 especificado. É útil para limpar buckets de deploy antes de uma nova implantação, garantindo que não existam arquivos antigos residuais.

## Arquitetura

### Arquivos

- **[lambda_function.py](lambda_function.py)** - Entry point do Lambda, delega para a função principal
- **[s3.py](s3.py)** - Contém a lógica principal de limpeza do bucket S3

### Fluxo de Execução

1. Lambda é invocado pelo CodePipeline
2. **Valida a estrutura do evento** e extrai o job ID
3. Extrai o nome do bucket dos parâmetros do job (`UserParameters`)
4. **Valida o nome do bucket** (não vazio, formato correto)
5. **Verifica se o bucket existe** e se há permissão de acesso
6. **Conta os objetos** no bucket antes da deleção
7. Deleta todos os objetos do bucket especificado
8. **Registra métricas** (quantidade de objetos deletados, tempo de execução)
9. Reporta sucesso ou falha de volta ao CodePipeline

## Integração com AWS

### Serviços Utilizados

- **AWS CodePipeline** - Trigger e notificação de status
- **Amazon S3** - Operações de deleção de objetos
- **AWS Lambda** - Execução da função

### Estrutura do Evento

A função espera um evento do CodePipeline com a seguinte estrutura:

```json
{
  "CodePipeline.job": {
    "id": "job-id",
    "data": {
      "actionConfiguration": {
        "configuration": {
          "UserParameters": "nome-do-bucket-s3"
        }
      }
    }
  }
}
```

## Permissões IAM Necessárias

A função Lambda precisa das seguintes permissões:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:DeleteObject",
        "s3:HeadBucket"
      ],
      "Resource": [
        "arn:aws:s3:::bucket-name",
        "arn:aws:s3:::bucket-name/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "codepipeline:PutJobSuccessResult",
        "codepipeline:PutJobFailureResult"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

**Nota**: A permissão `s3:HeadBucket` é necessária para validar a existência do bucket antes da deleção.

## Deploy

### Pré-requisitos

- Python 3.x
- AWS CLI configurado
- Permissões para criar/atualizar funções Lambda

### Criar o Pacote de Deploy

```bash
# Criar o arquivo zip com as dependências
zip -r function.zip lambda_function.py s3.py
```

### Deploy via AWS CLI

```bash
# Criar a função Lambda
aws lambda create-function \
  --function-name gt-clear-s3-deploy \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip

# Atualizar função existente
aws lambda update-function-code \
  --function-name gt-clear-s3-deploy \
  --zip-file fileb://function.zip
```

### Deploy via Infrastructure as Code

Recomenda-se usar Terraform, CloudFormation ou AWS SAM para gerenciar o deploy de forma automatizada.

## Tratamento de Erros

A função possui um sistema robusto de tratamento de erros:

### Validações Preventivas

- **Estrutura do evento**: Verifica se o evento possui a estrutura esperada do CodePipeline
- **Job ID**: Valida se o ID do job está presente
- **Nome do bucket**: Valida se o nome não está vazio ou com espaços inválidos
- **Existência do bucket**: Verifica se o bucket existe antes de tentar deletar
- **Permissões**: Detecta e reporta erros de acesso (403 Forbidden)

### Níveis de Tratamento

1. **ClientError (boto3)** - Captura erros específicos do AWS SDK
   - Identifica códigos de erro (404, 403, etc.)
   - Mensagens de erro estruturadas com código e descrição

2. **ValueError** - Captura erros de validação
   - Evento malformado
   - Bucket não encontrado
   - Parâmetros inválidos

3. **Exception genérica** - Captura qualquer outro erro não previsto
   - Stack trace completo nos logs
   - Mensagem de erro serializada corretamente

Todos os casos reportam a falha ao CodePipeline via `put_job_failure_result()` com mensagens descritivas.

## Desenvolvimento

### Estrutura do Código

```
function-gt-clear-s3-deploy/
├── lambda_function.py    # Handler principal
├── s3.py                # Lógica de limpeza S3
├── CLAUDE.md           # Documentação para Claude Code
└── README.md           # Este arquivo
```

### Logs

A função utiliza o módulo `logging` do Python para gerar logs estruturados no CloudWatch Logs:

**Logs de Sucesso:**
```
[INFO] Evento recebido do CodePipeline
[INFO] Iniciando limpeza do bucket: my-deploy-bucket
[INFO] Bucket 'my-deploy-bucket' existe e é acessível
[INFO] Total de objetos a deletar: 247
[INFO] Deletados 247 objetos do bucket 'my-deploy-bucket'
[INFO] Limpeza concluída com sucesso em 3.42 segundos
```

**Logs de Erro:**
```
[ERROR] Erro do AWS SDK: 404 - NoSuchBucket
[ERROR] Bucket 'invalid-bucket' não existe
```

**Informações Registradas:**
- Evento completo recebido do CodePipeline
- Nome do bucket sendo processado
- Validação de existência do bucket
- Quantidade de objetos encontrados
- Quantidade de objetos deletados
- Tempo total de execução
- Stack trace completo em caso de erro

## Monitoramento

### Métricas do Lambda

Métricas importantes para monitorar no CloudWatch:

- **Invocações** - Número de execuções
- **Erros** - Falhas na execução
- **Duração** - Tempo de execução (varia com o número de objetos)
- **Throttles** - Limitações de concorrência

### Métricas Customizadas

A função retorna um objeto com métricas detalhadas:

```json
{
  "statusCode": 200,
  "bucket": "my-deploy-bucket",
  "objects_deleted": 247,
  "execution_time": 3.42
}
```

Estas métricas também são registradas nos logs e podem ser extraídas via CloudWatch Logs Insights:

```sql
fields @timestamp, bucket, objects_deleted, execution_time
| filter ispresent(objects_deleted)
| sort @timestamp desc
```

### Alertas Recomendados

- **Taxa de erro > 5%**: Indica problemas recorrentes
- **Duração > 5 minutos**: Pode indicar buckets muito grandes
- **Falhas de validação**: Buckets não encontrados ou sem permissão

## Considerações de Segurança

⚠️ **ATENÇÃO**: Esta função deleta **TODOS** os objetos do bucket especificado. Garanta que:

- O nome do bucket seja validado antes da execução
- Apenas buckets de deploy temporário sejam alvos
- A role IAM tenha permissões restritas aos buckets corretos
- Haja backups se necessário

### Validações de Segurança Implementadas

✅ **Validação de existência**: A função verifica se o bucket existe antes de deletar
✅ **Validação de permissões**: Detecta e reporta erros de acesso (403 Forbidden)
✅ **Validação de input**: Nome do bucket não pode estar vazio ou conter apenas espaços
✅ **Logs auditáveis**: Todas as operações são registradas no CloudWatch para auditoria
✅ **Mensagens de erro descritivas**: Facilita troubleshooting sem expor informações sensíveis

## Melhorias Implementadas

### Versão 2.0 (Atual)

- ✅ Logging estruturado com módulo `logging` do Python
- ✅ Validação de estrutura do evento do CodePipeline
- ✅ Validação de existência do bucket antes da deleção
- ✅ Tratamento robusto de erros com mensagens descritivas
- ✅ Métricas de observabilidade (objetos deletados, tempo de execução)
- ✅ Cliente CodePipeline criado dentro da função (evita conexões stale)
- ✅ Retorno estruturado para facilitar testes
- ✅ Indentação consistente em todo o código

### Versão 1.0 (Inicial)

- Funcionalidade básica de deleção de objetos S3
- Integração com CodePipeline

## Contato

Guide Tech Solutions
Guilherme Vilela - guilherme.vilela@guidetech.com.br