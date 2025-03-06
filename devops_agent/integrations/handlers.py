import base64
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import yaml
from devops_agent.logs.logging import logger


def write_docker_config(data: List[Dict[str, Any]], type: str):
    """Save Docker integration config."""

    # check for ecr
    logger.warning(f"type: {type}")
    if type == "AMAZONECR":
        logger.warning(f"data: {data}")
        container_registry = None
        for integ in data:
            if integ["category"] == "CONTAINER_REGISTRY":
                container_registry = integ["data"]["registryUrl"]
        authenticate_ecr(container_registry)
        return

    else:
        docker_dir = os.path.expanduser("~/.docker")
        Path(docker_dir).mkdir(parents=True, exist_ok=True)
        docker_config = os.path.join(docker_dir, "config.json")

        docker_data = create_docker_config(data)
        with open(docker_config, "w") as f:
            json.dump(docker_data, f, indent=2)
        os.chmod(docker_config, 0o600)
        return


def authenticate_ecr(registry_url: str):
    """Authenticate with ECR.

    `aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com`
    """

    # check for region
    region = registry_url.split(".")[-3]

    # run command
    result = subprocess.call(
        f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {registry_url}",
        shell=True,
    )
    logger.debug(f"Output of authenticate_ecr: {result}")


def write_aws_config(
    aws_config: Dict[str, Any], aws_credentials: Dict[str, Any]
) -> None:
    """Write AWS configuration to ~/.aws/config and credentials to ~/.aws/credentials.

    Args:
        aws_config: AWS configuration dictionary.
        aws_credentials: AWS credentials dictionary.
    """

    try:
        aws_dir = os.path.expanduser("~/.aws")
        Path(aws_dir).mkdir(parents=True, exist_ok=True)
        aws_config_path = os.path.join(aws_dir, "config")
        aws_credentials_path = os.path.join(aws_dir, "credentials")

        # delete existing credentials and config if
        if os.path.exists(aws_config_path):
            os.remove(aws_config_path)
        if os.path.exists(aws_credentials_path):
            os.remove(aws_credentials_path)

        # write config in INI format
        with open(aws_config_path, "w+") as f:
            f.write(f"[default]\n")
            for config_key, config_value in aws_config.items():
                f.write(f"{config_key} = {config_value}\n")

        # write credentials in INI format
        with open(aws_credentials_path, "w+") as f:
            f.write(f"[default]\n")
            for config_key, config_value in aws_credentials.items():
                f.write(f"{config_key} = {config_value}\n")

    except Exception as e:
        raise Exception(f"Failed to write AWS config: {str(e)}")


def create_docker_config(registry_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create docker config.json format.

    Args:
        registry_configs: List of registry configurations

    Returns:
        Docker auth configuration dictionary
    """
    auths = {}
    for reg in registry_configs:
        if reg["category"] == "CONTAINER_REGISTRY":
            auths[reg["data"]["url"]] = {
                "auth": encode_docker_auth(
                    reg["data"]["username"], reg["data"]["password"]
                )
            }
    return {"auths": auths}


# Container Registry Functions
def encode_docker_auth(username: str, password: str) -> str:
    """Encode docker credentials in base64.

    Args:
        username: Docker registry username
        password: Docker registry password

    Returns:
        Base64 encoded auth string
    """
    auth_str = f"{username}:{password}"
    return base64.b64encode(auth_str.encode()).decode()


def write_kube_config(kube_config: Dict[str, Any]) -> None:
    """Write kubernetes config to ~/.kube/config.

    Args:
        kube_config: Kubernetes configuration dictionary

    Raises:
        Exception: If writing config fails
    """
    try:
        kube_dir = os.path.expanduser("~/.kube")
        Path(kube_dir).mkdir(parents=True, exist_ok=True)
        kube_config_path = os.path.join(kube_dir, "config")

        # Write config in YAML format
        with open(kube_config_path, "w") as f:
            yaml.safe_dump(kube_config, f)

        # Set proper permissions
        os.chmod(kube_config_path, 0o600)
    except Exception as e:
        raise Exception(f"Failed to write kube config: {str(e)}")


def write_eks_config(eks_config: Dict[str, Any]) -> None:
    """Write EKS config to ~/.kube/config.

    Args:
        eks_config: EKS configuration dictionary
    """
    # run aws cli command for EKS authentication
    try:
        result = subprocess.call(
            f"aws eks update-kubeconfig --name {eks_config['name']} --region {eks_config['region']}",
            shell=True,
        )
        logger.debug(f"Output of write_eks_config: {result}")
    except Exception as e:
        raise Exception(f"Failed to write EKS config: {str(e)}")


def handle_gcp_config(sa_json: Dict[str, Any], project_id: str) -> None:
    """Write GCP service account JSON to ~/.config/gcloud.

    Args:
        sa_json: GCP service account JSON

    Raises:
        Exception: If writing config fails
    """

    try:
        gcloud_dir = os.path.expanduser("~/.config/gcloud")
        Path(gcloud_dir).mkdir(parents=True, exist_ok=True)
        sa_json_path = os.path.join(gcloud_dir, "application_default_credentials.json")

        with open(sa_json_path, "w") as f:
            json.dump(sa_json, f, indent=2)

        os.chmod(sa_json_path, 0o600)
        try:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_json_path
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
            os.system(f"gcloud config set project {project_id}")
            os.system(f"gcloud auth activate-service-account --key-file={sa_json_path}")
        except Exception as ex:
            logger.error(
                f"Config updated, but failed to authenticate GCP service account: {str(ex)}"
            )
    except Exception as e:
        logger.error(f"Failed to write GCP config: {str(e)}")
        raise Exception(f"Failed to write GCP config: {str(e)}")


def write_jira_config(jira_config: List[Dict[str, Any]]) -> None:
    """Extract Jira configuration and set it as environment variables.

    Args:
        jira_config (List[Dict[str, Any]]): List of configuration dictionaries.

    Raises:
        ValueError: If Jira configuration is missing required fields.
    """
    try:
        jira_dir = os.path.expanduser("~/.config/jira")
        Path(jira_dir).mkdir(parents=True, exist_ok=True)
        sa_json_path = os.path.join(jira_dir, "application_default_credentials.json")

        with open(sa_json_path, "w") as f:
            json.dump(jira_config, f, indent=2)

        os.chmod(sa_json_path, 0o600)
        # Find the first JIRA config from the list
        jira_entry = next(
            (entry for entry in jira_config if entry["category"] == "SAAS"), None
        )

        if not jira_entry:
            raise ValueError("No valid JIRA configuration found.")

        # Extract data
        jira_data = jira_entry.get("data", {})
        print(jira_data, "jiradata")
        instance_url = jira_data.get("instanceUrl")
        api_token = jira_data.get("APIToken")
        email = jira_data.get("email")

        if not all([instance_url, api_token, email]):
            raise ValueError("JIRA configuration is missing required fields.")

        # Set environment variables
        os.environ["JIRA_INSTANCE_URL"] = instance_url
        os.environ["JIRA_API_TOKEN"] = api_token
        os.environ["JIRA_USERNAME"] = email
        os.environ["JIRA_CLOUD"] = "True"

        logger.info(
            "JIRA environment variables set successfully.", instance_url, api_token
        )

    except Exception as e:
        logger.error(f"Failed to configure JIRA: {e}")
        raise RuntimeError(f"JIRA configuration failed: {e}")
