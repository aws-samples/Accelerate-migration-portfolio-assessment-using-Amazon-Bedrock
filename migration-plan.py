import os
import json
import logging
import boto3
import csv
from io import StringIO
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize a Boto3 client for Bedrock
bedrock = boto3.client(service_name='bedrock-runtime')
bedrock_client = boto3.client(service_name='bedrock-agent-runtime')
s3 = boto3.client('s3')

def invoke_bedrock_model(prompt):
    try:
        body = {
            "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
            "contentType": "application/json",
            "accept": "application/json",
            "body": {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100000,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
        }
        
        # Invoke the Bedrock model
        response = bedrock.invoke_model(
            body=json.dumps(body['body']),
            modelId=body['modelId'],
            contentType=body['contentType'],
            accept=body['accept']
        )
        
        # Parse the response from Bedrock
        response_body = json.loads(response['body'].read())
        logger.info(f"Response from Bedrock model: {response_body}")
        
        # Extract the generated message from the response
        generated_content = response_body.get('content', [{}])[0].get('text', '')
        
        return generated_content.strip()
    except ClientError as e:
        logger.error("An error occurred while invoking Bedrock model: %s", e, exc_info=True)
        raise

def retrieve_from_qanda_knowledgebase(app_id, kb_id_qanda_info):
    query = (
        f"Provide all the information for application ID {app_id}, including the Migration Assessment Questions "
        f"and the corresponding App team Responses. Format the information as a structured list of questions and answers."
    )

    try:
        response = bedrock_client.retrieve_and_generate(
            input={
                'text': query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kb_id_qanda_info,
                    'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2'
                }
            }
        )

        retrieved_info = response['output']['text']
        print(f"Received KB info:  {retrieved_info}")
        return retrieved_info

    except ClientError as e:
        print(f"Error retrieving information from the Q&A knowledge base: {e}")
        return ""

def write_text_to_s3(bucket, key, content):
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=content)
    except ClientError as e:
        logger.error("Error writing text to S3: %s", e, exc_info=True)
        raise

def retrieve_from_app_knowledge_base(app_id, r_strategy, kb_id_migration_agent_info):
    # Prepare the query
    query = (
        f"Provide detailed information about application ID {app_id} related to its migration to AWS using the {r_strategy} strategy. "
        f"Include the following details:\n"
        f"- Current architecture, including server specifications (CPU, RAM, storage) and networking requirements\n"
        f"- Suitability of the application for various AWS compute services (EC2, ECS, EKS, Lambda) based on its architecture and requirements\n"
        f"- Recommended compute options and configurations for the application\n"
        f"- Database specifications (engine, version, size) and recommended RDS instance types\n"
        f"- Networking requirements, including ports, protocols, and bandwidth considerations\n"
        f"- Dependencies and third-party integrations\n"
        f"- Any specific migration considerations for {r_strategy}"
    )

    try:
        # Call the Bedrock KnowledgeBase retrieve_and_generate API
        response = bedrock_client.retrieve_and_generate(
            input={
                'text': query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kb_id_migration_agent_info,
                    'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
                }
            }
        )

        # Extract the relevant information from the response
        retrieved_info = response['output']['text']
        print(f"Received KB info:  {retrieved_info}")
        return retrieved_info

    except ClientError as e:
        print(f"Error retrieving information from the knowledge base: {e}")
        return ""    
    
def retrieve_from_knowledge_base(r_strategy, kb_id_bp_docs):
    # Prepare the query
    query = (
        f"Provide detailed guidance on creating a migration plan for an application moving to AWS using the {r_strategy} strategy. "
        f"Include key considerations for migrating compute resources, databases, and storage specific to {r_strategy}. "
        f"Outline the steps involved in the migration process and best practices to ensure a smooth transition with {r_strategy}."
    )

    try:
        # Call the Bedrock KnowledgeBase retrieve_and_generate API
        response = bedrock_client.retrieve_and_generate(
            input={
                'text': query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kb_id_bp_docs,
                    'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
                }
            }
        )

        # Extract the relevant information from the response
        retrieved_info = response['output']['text']
        print(f"Received KB info:  {retrieved_info}")
        return retrieved_info

    except ClientError as e:
        print(f"Error retrieving information from the knowledge base: {e}")
        return ""

def lambda_handler(event, context):
    try:
        print("Received event: " + json.dumps(event))
        properties = event['requestBody']['content']['application/json']['properties']
        params = {prop['name']: prop['value'] for prop in properties}
        
        s3_bucket = os.environ['S3_BUCKET']
        app_id = params['app_id']
        r_strategy = params['r_strategy']
        output_key = f"R-Disposition-outputs/{app_id}_migration_plan.txt"
        kb_id_migration_agent_info = os.environ['KB_ID_MIGRATION_AGENT_INFO'] 
        kb_id_bp_docs = os.environ['KB_ID_BP_DOCS'] 
        kb_id_qanda_info = os.environ['KB_ID_QANDA_INFO'] 
        
        retrieved_info = retrieve_from_knowledge_base(r_strategy,kb_id_bp_docs)
        retrieved_app_info = retrieve_from_app_knowledge_base(app_id, r_strategy, kb_id_migration_agent_info)
        
        qanda_info = retrieve_from_qanda_knowledgebase(app_id, kb_id_qanda_info)

        
        prompt = (
        f"Create a detailed migration plan for application ID {app_id} based on the following information:\n\n"
        f"Application details:\n{retrieved_app_info}\n\n"
        f"Migration Strategy: {r_strategy}\n\n"
        f"Migration recommendation from AWS whitepapers: {retrieved_info}\n\n"
        f"Application Assessment Data:\n{qanda_info}\n\n"
        "1. Introduction\n"
        "   - Provide a brief overview of the application, its purpose, and its current architecture\n"
        "   - Provide a detailed description of AWS architecture\n"
        f"   - Explain the rationale for choosing the {r_strategy} migration strategy\n\n"
        "2. Pre-Migration Activities\n"
        "   - AWS Account Enrollment and Setup with AWS landing zone or AWS control tower\n"
        "     - Provide step-by-step instructions for enrolling AWS accounts with control tower or AWS landing Zone\n"
        "     - Include guidelines for setting up development and production accounts\n"
        "   - Application Assessment and Dependencies Analysis\n"
        "     - Identify and list all dependencies, including third-party integrations and libraries\n"
        "     - Assess compatibility with AWS services and potential migration challenges\n"
        "   - Data Assessment and Migration Planning\n"
        "     - Analyze data sources, volumes, and formats\n"
        "     - Outline the plan for data migration, including any necessary data transformations\n"
        "   - Licensing and Compliance Review\n"
        "     - Review the application's licensing model and ensure compliance with AWS\n"
        "     - Address any legal or regulatory requirements related to the migration\n"
        "   - Security and Compliance Planning\n"
        "     - Identify and plan the implementation of necessary security controls and best practices\n"
        "     - Ensure compliance with industry standards and regulations (e.g., HIPAA, PCI-DSS)\n"
        "     - Configure AWS Identity and Access Management (IAM) roles and policies\n"
        "   - Network and Connectivity Planning\n"
        "     - Design the target network architecture on AWS\n"
        "     - Configure Virtual Private Cloud (VPC), subnets, and security groups\n"
        "     - Establish connectivity between on-premises and AWS environments (e.g., VPN, AWS Direct Connect)\n"
        "   - Migration Tooling and Environment Setup\n"
        "     - List the AWS tools and services that will be used for the migration (e.g., AWS MGN, AWS DMS)\n"
        "     - Provide step-by-step instructions for setting up the necessary AWS environments\n\n"
        "3. Compute, Database, and Storage Migration\n"
        "   - Compute Migration\n"
        "     - Provide a detailed, step-by-step plan for migrating compute resources\n"
        "     - Include specific instructions for using AWS services like AWS MGN or AWS App2Container\n"
        "     - Based on the application's architecture and requirements, evaluate its suitability for various AWS compute services (EC2, ECS, EKS, Lambda)\n"
        "     - Provide recommendations for the most appropriate compute option(s) and configurations\n"
        "     - If using EC2, recommend appropriate instance types based on performance and scalability needs\n"
        "     - If using containers (ECS or EKS), provide guidance on containerization, orchestration, and cluster configurations\n"
        "     - If using Lambda, identify suitable components for serverless migration and provide recommendations on function design and triggers\n\n"
        "   - Database Migration\n"
        "     - Outline the database migration process, including the use of AWS DMS or native database tools\n"
        "     - Provide detailed instructions for configuring the target database on AWS (e.g., Amazon RDS, Amazon Aurora)\n"
        "     - Based on the current database specifications, recommend appropriate RDS instance types\n"
        "     - Provide a mapping of the current database configurations to the corresponding RDS instances\n"
        "     - Include details on database engine, version, size, and performance requirements\n"
        "     - Address any database optimizations or schema changes required\n\n"
        "   - Storage Migration\n"
        "     - Provide a step-by-step plan for migrating storage, including the use of AWS DataSync or AWS Transfer Family\n"
        "     - Include instructions for configuring and optimizing storage on AWS (e.g., Amazon EFS, Amazon S3)\n"
        "     - Address any data synchronization or replication requirements\n"
        "     - Provide recommendations for storage options based on the current storage requirements\n"
        "     - Include details on storage size, performance, and data transfer considerations\n\n"
        "4. Testing and Validation\n"
        "   - Define a comprehensive testing strategy, including functional, performance, and user acceptance testing\n"
        "   - Provide detailed test cases and scenarios for each testing phase\n"
        "   - Include instructions for setting up test environments on AWS\n"
        "   - Clearly define success criteria and acceptance criteria for each testing phase\n\n"
        "5. Monitoring, Logging, and Cost Optimization\n"
        "   - Monitoring and Logging\n"
        "     - Configure Amazon CloudWatch for resource monitoring and alerting\n"
        "     - Enable AWS CloudTrail for API activity tracking and auditing\n"
        "     - Implement centralized logging solutions (e.g., Amazon Elasticsearch Service, AWS Centralized Logging)\n"
        "   - Cost Optimization\n"
        "     - Right-size resources based on performance requirements\n"
        "     - Leverage AWS cost optimization tools (e.g., AWS Cost Explorer, AWS Budgets)\n"
        "     - Implement cost-saving measures (e.g., reserved instances, spot instances, auto-scaling)\n\n"
        "6. Disaster Recovery and Business Continuity\n"
        "   - Design a highly available and fault-tolerant architecture\n"
        "   - Implement data backup and restore procedures\n"
        "   - Develop and test disaster recovery plans\n\n"
        "7. Cutover and Post-Migration\n"
        "   - Develop a detailed cutover plan, including timelines, communication plans, and rollback procedures\n"
        "   - Provide step-by-step instructions for the cutover process\n"
        "   - Outline post-migration activities, such as monitoring, optimization, and knowledge transfer\n"
        "   - Include a plan for decommissioning the old environment\n\n"
        "8. Stakeholder Communication and Collaboration\n"
        "   - Identify key stakeholders and their roles in the migration process\n"
        "   - Establish communication channels and feedback loops\n"
        "   - Conduct regular status updates and progress reviews\n\n"
        "9. Risk Assessment and Mitigation\n"
        "    - Identify potential risks associated with the migration, including technical, operational, and business risks\n"
        "    - Provide specific mitigation strategies for each identified risk\n"
        "    - Include a contingency plan and detailed rollback procedures\n\n"
        "10. Training and Continuous Optimization\n"
        "    - Outline a comprehensive training plan for the team, including AWS services, architecture, and application-specific knowledge\n"
        "    - Provide a schedule for training sessions and knowledge transfer activities\n"
        "    - Establish a process for continuous optimization and modernization post-migration\n"
        "    - Include recommendations for leveraging additional AWS services and best practices\n\n"
        "Ensure the plan is well-structured, provides actionable guidance, and includes specific instructions for each phase of the migration process. Use consistent formatting and language throughout the plan."
    )
        
        #print(f"Received final prompt:  {prompt}")

        # Invoke Bedrock model to get the migration plan
        migration_plan = invoke_bedrock_model(prompt)
        
        # Write the migration plan to a text file in S3
        write_text_to_s3(s3_bucket, output_key, migration_plan)
        
        # Construct the API response
        response_body = {
            'application/json': {
                'body': output_key
            }
        }

        action_response = {
            'actionGroup': event['actionGroup'],
            'apiPath': event['apiPath'],
            'httpMethod': event['httpMethod'],
            'httpStatusCode': 200,
            'responseBody': response_body
        }
         
        session_attributes = event['sessionAttributes']
        prompt_session_attributes = event['promptSessionAttributes']
        
        api_response = {
            'messageVersion': '1.0', 
            'response': action_response,
            'sessionAttributes': session_attributes,
            'promptSessionAttributes': prompt_session_attributes
        }
    
        print(api_response)
        return api_response
            
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                "error": "An error occurred during the process.",
                "details": str(e)
            })
        }