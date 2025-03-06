import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from devops_agent.integrations import handlers
from devops_agent.logs.logging import logger


def do_save_integrations(data: List[Dict[str, Any]]) -> None:
    """Save integration configurations to respective locations.

    Args:
        data: List of integration configurations
    """
    try:
        # Save original config
        config_dir = os.path.expanduser("~/.devops-gpt")
        Path(config_dir).mkdir(parents=True, exist_ok=True)
        config_file = os.path.join(config_dir, "config")
        with open(config_file, "w") as f:
            json.dump({"data": data}, f, indent=2)

        # Process each integration
        for integration in data:
            # logger.info(f"Processing integration: {integration['name']}")
            if integration["category"] == "CONTAINER_REGISTRY":
                handlers.write_docker_config(data, type=integration["type"])
            elif integration["category"] == "KUBERNETES_CLUSTER":
                if integration["type"] == "CLUSTER":
                    handlers.write_kube_config(integration["data"]["kubeConfig"])
                elif integration["type"] == "EKS":
                    handlers.write_eks_config(
                        {
                            "name": integration["data"]["clusterName"],
                            "region": integration["data"]["awsRegion"],
                        }
                    )
            elif integration["category"] == "VERSION_CONTROL":
                # TODO: Implement GitHub config
                # TODO: Implement Gitlab config
                # TODO: Implement Bitbucket config
                pass
            elif integration["category"] == "CLOUD_PROVIDER":
                cloud_provider = integration["type"]
                if cloud_provider == "AWS":
                    # fetch aws config and credentials
                    aws_credentials = {
                        "aws_access_key_id": integration["data"]["awsAccessKeyId"],
                        "aws_secret_access_key": integration["data"][
                            "awsSecretAccessKey"
                        ],
                    }
                    aws_config = {
                        "region": integration["data"]["awsRegion"],
                        "output": integration["data"]["awsOutputFormat"],
                    }
                    handlers.write_aws_config(aws_config, aws_credentials)
                elif cloud_provider == "GCP":
                    handlers.handle_gcp_config(
                        integration["data"]["serviceAccountKey"],
                        integration["data"]["serviceAccountKey"]["project_id"],
                    )
                elif cloud_provider == "AZURE":
                    # TODO: Implement Azure config
                    pass
            elif integration["category"] == "CICD":
                # TODO: Implement Jenkins config
                # TODO: Implement CircleCI config
                # TODO: Implement ArgoCD config
                pass
            elif integration["category"] == "OBSERVABILITY":
                # TODO: Implement Grafana config
                # TODO: Implement Loki config
                # TODO: Implement Mimir config
                # TODO: Implement Tempo config
                pass
            elif integration["category"] == "SAAS":
                if integration["type"] == "JIRA":
                    handlers.write_jira_config(data)

                pass
    except Exception as e:
        raise Exception(f"Failed to save integrations: {str(e)}")


def do_get_integrations() -> Dict[str, Any]:
    """Get current integrations configuration.

    Returns:
        Dict containing integration configurations

    Raises:
        FileNotFoundError: If config file doesn't exist
        JSONDecodeError: If config file is invalid
    """
    config_file = os.path.join(os.path.expanduser("~/.devops-gpt"), "config")
    if not os.path.exists(config_file):
        raise FileNotFoundError("Configuration file not found")

    with open(config_file, "r") as f:
        config = json.load(f)

    return config
