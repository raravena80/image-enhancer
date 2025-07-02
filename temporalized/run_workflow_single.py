import asyncio
import logging
from temporalio.client import Client
from workflows import ImageEnhancementWorkflow
from activities import ImageProcessingConfig, S3Location
import os
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Configure logging
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_image_enhancement_workflow():
    """
    Start an image enhancement workflow execution.
    """
    # Get Temporal server configuration
    temporal_address = os.getenv('TEMPORAL_ADDRESS', 'localhost:7233')
    temporal_namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
    task_queue = os.getenv('TEMPORAL_TASK_QUEUE', 'image-enhancement-queue')
    
    # Get workflow configuration from environment
    source_bucket = os.getenv('SOURCE_BUCKET', 'ricardotemporal')
    source_key = os.getenv('SOURCE_KEY', 'funny.png')
    dest_bucket = os.getenv('DEST_BUCKET', 'ricardotemporalprocessed')
    dest_key = os.getenv('DEST_KEY', 'enhanced_funny.png')
    enhancement_prompt = os.getenv('ENHANCEMENT_PROMPT', 
                                 'Make this image more vibrant, increase clarity and sharpness, improve lighting')
    
    # AWS and OpenAI configuration
    config = ImageProcessingConfig(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_region=os.getenv('AWS_REGION', 'us-east-1'),
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Debug: Check if credentials are loaded
    logger.info(f"AWS Region: {config.aws_region}")
    logger.info(f"AWS Access Key ID loaded: {'Yes' if config.aws_access_key_id else 'No'}")
    logger.info(f"AWS Secret Key loaded: {'Yes' if config.aws_secret_access_key else 'No'}")
    logger.info(f"OpenAI API Key loaded: {'Yes' if config.openai_api_key else 'No'}")
    
    source_location = S3Location(bucket=source_bucket, key=source_key)
    dest_location = S3Location(bucket=dest_bucket, key=dest_key)
    
    logger.info(f"Connecting to Temporal server at {temporal_address}")
    logger.info(f"Processing: s3://{source_bucket}/{source_key} -> s3://{dest_bucket}/{dest_key}")
    
    try:
        # Connect to Temporal server
        client = await Client.connect(temporal_address, namespace=temporal_namespace)
        
        # Generate a unique workflow ID
        workflow_id = f"image-enhancement-{uuid.uuid4()}"
        
        logger.info(f"Starting workflow with ID: {workflow_id}")
        
        # Start the workflow
        handle = await client.start_workflow(
            ImageEnhancementWorkflow.run,
            args=[config, source_location, dest_location, enhancement_prompt],
            id=workflow_id,
            task_queue=task_queue,
        )
        
        logger.info(f"Workflow started. Workflow ID: {handle.id}")
        logger.info("Waiting for workflow to complete...")
        
        # Wait for workflow to complete and get result
        result = await handle.result()
        
        logger.info(f"Workflow completed successfully!")
        logger.info(f"Result: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error running workflow: {e}")
        raise

async def main():
    """
    Main function to run the workflow.
    """
    try:
        result = await run_image_enhancement_workflow()
        print(f"\n✅ Success: {result}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
