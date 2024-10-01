# AWS Migration Assessment and Planning Tool

## Overview
This tool provides an AI-powered solution for assessing and planning the migration of applications to AWS. It leverages Amazon Bedrock for intelligent analysis and recommendations based on application-specific data and best practices.

## How It Works
1. Users interact with the migration assistant through the Amazon Bedrock chat console.
2. The migration assistant uses Amazon Bedrock agents configured with instructions, action groups, and knowledge bases.
3. Based on user requests, the assistant invokes relevant action groups, which trigger specific AWS Lambda functions.
4. Lambda functions use Retrieval Augmented Generation (RAG) to process requests and generate outputs.
5. Output documents are uploaded to a designated Amazon S3 bucket.

### Detailed Workflow
1. User Input: Users interact with the migration assistant via the Amazon Bedrock chat console. They can request actions like:
   - "Generate R-disposition with cost estimates for A1-CRM"
   - "Generate Migration plan for A2-CMDB"

2. Request Processing: The migration assistant, powered by Amazon Bedrock agents, processes these requests using predefined action groups:
   - R Dispositions action group
   - Migration Plan action group

3. Lambda Function Execution: These action groups trigger specific AWS Lambda functions:
   - `r-disposition-assessment.py` for R-Dispositions
   - `migration-plan.py` for Migration Plans

4. RAG-based Analysis: Lambda functions use Retrieval Augmented Generation (RAG) to:
   - Fetch relevant data from knowledge bases
   - Generate AI-powered analyses and recommendations

5. Output Storage: The resulting documents (R-Dispositions with cost estimates, Migration Plans) are uploaded to a designated Amazon S3 bucket for user access.

## Repository Contents
- `Example-output-from-Application-Discovery-agent.png`: Sample infrastructure data used as input
- `example-migration-questions.png`: Example of application-specific migration assessment questions and answers
- `migration-plan.py`: Lambda function for generating detailed migration plans
- `r-disposition-assessment.py`: Lambda function for assessing multiple applications and providing migration recommendations

## Prerequisites
- AWS account with access to Lambda, S3, and Bedrock services
- Python 3.8+
- Boto3 library
- AWS CLI configured with appropriate permissions

## Setup
1. Clone this repository
2. Set up Amazon Bedrock knowledge bases:
   - kb_id_migration_agent_info: For infrastructure and application data
   - kb_id_qanda_info: For migration assessment Q&A data
   - kb_id_bp_docs: For AWS migration best practices and recommendations
3. Configure environment variables in your Lambda functions:
   - S3_BUCKET: The S3 bucket for storing outputs
   - KB_ID_MIGRATION_AGENT_INFO: ID of the infrastructure knowledge base
   - KB_ID_QANDA_INFO: ID of the Q&A knowledge base
   - KB_ID_BP_DOCS: ID of the best practices knowledge base
4. Set up Amazon Bedrock agents with appropriate action groups and knowledge bases

## Usage

### Generating a Migration Plan
Use the Bedrock chat console to request a migration plan for a specific application.

Example input:
"Generate Migration plan for A1-CRM"

Output:
- A detailed migration plan stored in S3 as a text file

### Assessing Multiple Applications
Use the Bedrock chat console to request R-dispositions for multiple applications.

Example input:
"Generate R-disposition with cost estimates for A1-CRM, A2-CMDB"

Output:
- A CSV file in S3 containing migration recommendations and cost estimates for each application

## Data Inputs
- Infrastructure data (Example-output-from-Application-Discovery-agent.png): Provides details on servers, applications, and databases.
- Migration assessment Q&A (example-migration-questions.png): Offers insights into application-specific migration considerations.

## Best Practices
- Regularly update the knowledge bases with the latest application and infrastructure data.
- Review and validate AI-generated recommendations before implementation.
- Use the tool as part of a broader migration strategy that includes human expertise and AWS best practices.

## Troubleshooting
- Ensure all required environment variables are set correctly in Lambda functions.
- Check CloudWatch logs for detailed error messages if the Lambda functions fail.
- Verify that the Bedrock knowledge bases are properly populated with up-to-date information.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

