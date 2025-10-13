import os
from dotenv import load_dotenv
from core.utils.log_manager.log_manager import log_error


def get_secret(secret_name):
    try:
        load_dotenv()
    except Exception as e:
        log_error("Failed to load environment variables from .env file", e)
        raise
    
    env_var_name = secret_name.replace("-", "_").upper()
    secret_value = os.getenv(env_var_name)
    
    if secret_value:
        return secret_value
    else:
        error_msg = f"Secret '{env_var_name}' not found in .env file"
        log_error(f"Secret retrieval failed for {secret_name}: {error_msg}",
                  ValueError(error_msg))
        raise ValueError(error_msg)


def get_cognito_secrets():
    try:
        cognito_key = get_secret("AWS-Cognito-Key")
        cognito_secret = get_secret("AWS-Cognito-Secret")
        cognito_user_pool_id = get_secret("AWS-Cognito-User-Pool-ID")
        
        return cognito_key, cognito_secret, cognito_user_pool_id
        
    except Exception as e:
        log_error("Failed to retrieve Cognito credentials", e)
        raise


def get_marketo_secrets():
    try:
        marketo_base_url = get_secret("Marketo-Base-URL")
        marketo_client_id = get_secret("Marketo-Client-ID")
        marketo_client_secret = get_secret("Marketo-Client-Secret")
        
        return marketo_base_url, marketo_client_id, marketo_client_secret
        
    except Exception as e:
        log_error("Failed to retrieve Marketo credentials", e)
        raise


def get_openai_secrets():
    try:
        openai_api_key = get_secret("OpenAI-API-Key")
        
        return openai_api_key
        
    except Exception as e:
        log_error("Failed to retrieve OpenAI credentials", e)
        raise


def get_optimizely_secrets():
    try:
        opti_base_url = get_secret("OPTI-Base-URL")
        opti_client_id = get_secret("OPTI-Client-ID")
        opti_client_secret = get_secret("OPTI-Client-Secret")
        opti_username = get_secret("OPTI-Username")
        opti_password = get_secret("OPTI-Password")
        opti_storefront_username = get_secret("OPTI-Storefront-Username")
        opti_storefront_password = get_secret("OPTI-Storefront-Password")
        
        return {
            'base_url': opti_base_url,
            'client_id': opti_client_id,
            'client_secret': opti_client_secret,
            'username': opti_username,
            'password': opti_password,
            'storefront_username': opti_storefront_username,
            'storefront_password': opti_storefront_password
        }
        
    except Exception as e:
        log_error("Failed to retrieve Optimizely credentials", e)
        raise


def get_outlook_secrets():
    try:
        outlook_client_id = get_secret("Outlook-Client-ID")
        outlook_client_secret = get_secret("Outlook-Client-Secret")
        outlook_tenant_id = get_secret("Outlook-Tenant-ID")
        outlook_mailbox_id = get_secret("Outlook-Mailbox-ID")
        
        return {
            'client_id': outlook_client_id,
            'client_secret': outlook_client_secret,
            'tenant_id': outlook_tenant_id,
            'mailbox_id': outlook_mailbox_id
        }
        
    except Exception as e:
        log_error("Failed to retrieve Outlook credentials", e)
        raise


def get_asana_secrets():
    try:
        asana_token = get_secret("ASANA-Token")
        asana_project_id = get_secret("ASANA-Project-ID")
        asana_user_gid = get_secret("ASANA-User-GID")
        asana_workspace_id = get_secret("ASANA-Workspace-ID")
        return {
            'token': asana_token,
            'project_id': asana_project_id,
            'user_gid': asana_user_gid,
            'workspace_id': asana_workspace_id
        }
    except Exception as e:
        log_error("Failed to retrieve Asana credentials", e)
        raise