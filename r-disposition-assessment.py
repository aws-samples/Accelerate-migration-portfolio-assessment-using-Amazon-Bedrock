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
                "max_tokens": 10000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
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
        print(f"Received KB info: {retrieved_info}")
        return retrieved_info

    except ClientError as e:
        print(f"Error retrieving information from the Q&A knowledge base: {e}")
        return ""
    
def write_csv_to_s3(bucket, key, rows):
    try:
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerows(rows)
        s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue())
    except ClientError as e:
        logger.error("Error writing CSV to S3: %s", e, exc_info=True)
        raise

def retrieve_from_app_knowledge_base(app_id, kb_id_migration_agent_info):
    # Prepare the query
    query = (
        f"Provide a comprehensive overview of application ID {app_id}, including its description, "
        f"business unit, criticality, and type. Additionally, detail its dependencies on other applications, "
        f"the server(s) it is associated with, and the databases it utilizes. Highlight any critical dependencies, "
        f"the role of its server infrastructure, and the importance of its database connections."
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
                    'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2'
                }
            }
        )

        # Extract the relevant information from the response
        retrieved_info = response['output']['text']
        print(f"Received KB info: {retrieved_info}")
        return retrieved_info

    except ClientError as e:
        print(f"Error retrieving information from the knowledge base: {e}")
        return ""    
    
def retrieve_from_knowledge_base(kb_id_bp_docs):
    # Prepare the query
    query = (
        "Provide a migration recommendation for an application moving to AWS, focusing on the optimal migration strategy "
        "based on the application's characteristics, requirements, and goals. Consider factors such as application complexity, "
        "coupling, performance needs, scalability, data dependencies, and compliance requirements. "
        "Evaluate the suitability of different migration strategies, including rehosting, replatforming, refactoring, and rearchitecting. "
        "Provide guidance on selecting the most appropriate strategy or combination of strategies to achieve a successful migration. "
        "Include insights from AWS Migration Lens and other relevant best practices to support your recommendation."
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
                    'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2'
                }
            }
        )

        # Extract the relevant information from the response
        retrieved_info = response['output']['text']
        print(f"Received KB info: {retrieved_info}")
        return retrieved_info

    except ClientError as e:
        print(f"Error retrieving information from the knowledge base: {e}")
        return ""

def parse_recommendation(recommendation):
    patterns = ''
    justification = ''
    aws_architecture = ''
    approximate_cost = ''

    sections = recommendation.split('\n')
    
    in_patterns = False
    in_justification = False
    in_architecture = False
    in_cost = False

    for line in sections:
        line = line.strip()
        
        if line.startswith('1. Top 3 Recommended Migration Patterns:'):
            in_patterns = True
            in_justification = False
            in_architecture = False
            in_cost = False
            patterns += line + '\n'
        elif line.startswith('2. Justification:'):
            in_justification = True
            in_patterns = False
            in_architecture = False
            in_cost = False
            justification += line + '\n'
        elif line.startswith('3. Potential AWS Architecture:'):
            in_architecture = True
            in_patterns = False
            in_justification = False
            in_cost = False
            aws_architecture += line + '\n'
        elif line.startswith('4. Cost Breakdown and Total Cost for each Migration Pattern:'):
            in_cost = True
            in_patterns = False
            in_justification = False
            in_architecture = False
            approximate_cost += line + '\n'
        else:
            if in_patterns and line:
                patterns += line + '\n'
            elif in_justification and line:
                justification += line + '\n'
            elif in_architecture and line:
                aws_architecture += line + '\n'
            elif in_cost and line:
                approximate_cost += line + '\n'
    
    patterns = patterns.strip()
    justification = justification.strip()
    aws_architecture = aws_architecture.strip()
    approximate_cost = approximate_cost.strip()

    return patterns, justification, aws_architecture, approximate_cost

def lambda_handler(event, context):
    try:
        print("Received event: " + json.dumps(event))
        properties = event['requestBody']['content']['application/json']['properties']
        params = {prop['name']: prop['value'] for prop in properties}
        
        s3_bucket = os.environ['S3_BUCKET']
        app_ids = params['app_ids'].split(',')
        output_csv_key = f"R-Disposition-outputs/r_disposition_recommendations.csv"
        kb_id_migration_agent_info = os.environ['KB_ID_MIGRATION_AGENT_INFO'] 
        kb_id_bp_docs = os.environ['KB_ID_BP_DOCS'] 
        kb_id_qanda_info = os.environ['KB_ID_QANDA_INFO'] 

        
        retrieved_info = retrieve_from_knowledge_base(kb_id_bp_docs)
        
        recommendations = [['App-id', 'Top 3 Recommended Migration Patterns', 'Justification', 'Potential AWS Architecture', 'Approximate Cost']]
        
        for app_id in app_ids:
            retrieved_app_info = retrieve_from_app_knowledge_base(app_id, kb_id_migration_agent_info)
            qanda_info = retrieve_from_qanda_knowledgebase(app_id, kb_id_qanda_info)
            
            prompt = (
                "As an AWS migration expert, your task is to analyze the following application migration readiness data and recommend the most suitable migration patterns for migrating the application to AWS. The migration patterns to consider are:\n"
                "- Retain\n"
                "- Retire\n"
                "- Rehost\n"
                "- Replatform\n"
                "- Repurchase\n"
                "- Refactor\n\n"
                "In addition to the application migration readiness data, consider the following relevant information retrieved from the knowledge base:\n"
                f"{retrieved_info}\n\n"
                "Application-specific information:\n"
                f"{retrieved_app_info}\n\n"
                "Application Q&A information:\n"
                f"{qanda_info}\n\n"
                "When providing your recommendation, please ensure that all suggestions are directly supported by the information provided in the application migration readiness data, the application-specific information, and the Q&A information. If a recommendation is based on an assumption or information not explicitly mentioned in the data, please clarify that in your response.\n\n"
                "Please include the following details in your recommendation:\n"
                "1. Top 3 Recommended Migration Patterns: [Provide the top 3 recommended migration patterns along with their respective percentages, e.g., Refactor-70%, Replatform-20%, Rehost-10%]\n"
                "2. Justification: [For each recommended migration pattern, provide a detailed explanation of why it is suitable based on the application's characteristics, requirements, and migration goals. Analyze the key factors that influenced your decision, taking into account the complexity, time/velocity, cost, and optimization considerations. Cite specific information from the application readiness data, the application-specific information, and the Q&A information that supports your recommendation.]\n"
                "3. Potential AWS Architecture: [For each recommended migration pattern, provide a high-level description of the potential AWS architecture that could be implemented. Include the key AWS services, components, and architectural patterns that align with the migration pattern and the application's requirements.]\n\n"
                "Please provide your detailed recommendation based on the above information, guidelines, and the retrieved insights from the knowledge base, including the application-specific information and Q&A information. Ensure that all suggestions are supported by the provided data. If additional information is required to make a more accurate recommendation, please state the specific details needed.\n\n"
                "4. Cost Breakdown and Total Cost for each Migration Pattern: [For each recommended migration pattern, provide a detailed cost breakdown at the AWS resource level, listing the individual AWS services, their pricing models (e.g., hourly, monthly, data transfer), and the estimated costs based on the application's requirements and usage patterns. Additionally, provide the total estimated cost for implementing each migration pattern's AWS architecture, considering all relevant factors.]"
                "Provide your response in a clear, well-structured format, using bullet points, numbering, or headings as appropriate to enhance readability."
            )
            print(f"Received final prompt: {prompt}")

            recommendation = invoke_bedrock_model(prompt)
            patterns, justification, aws_architecture, approximate_cost = parse_recommendation(recommendation)
            recommendations.append([app_id, patterns, justification, aws_architecture, approximate_cost])
        
        write_csv_to_s3(s3_bucket, output_csv_key, recommendations)
        
        response_body = {
            'application/json': {
                'body': output_csv_key
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
