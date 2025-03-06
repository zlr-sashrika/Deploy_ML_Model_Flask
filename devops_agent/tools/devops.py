import os
import shlex
import subprocess
from typing import cast

from devops_agent.logs.logging import logger
from devops_agent.rag.constants import bq_rag, confluence_rag, docker_rag, aws_rag
from devops_agent.states.devops import AgentState
from dotenv import load_dotenv
from langchain.agents import AgentType, initialize_agent
from langchain_community.agent_toolkits.jira.toolkit import JiraToolkit
from langchain_community.utilities.jira import JiraAPIWrapper
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

load_dotenv(os.path.join(os.getcwd(), ".env"))
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,  # , base_url="https://openrouter.ai/api/v1"
)
from devops_agent.logs.logging import logger
from devops_agent.rag.devops import vectorstore_devops


@tool
def reset_credentials(state: AgentState, config: RunnableConfig):
    """A tool that resets the context in state object."""

    ai_message = cast(AIMessage, state["messages"][-2])
    tool_message = cast(ToolMessage, state["messages"][-1])
    state["context"] = []
    return state


@tool
def kubectl_exec(command: str) -> str:
    """A tool that executes kubectl commands.

    Args:
        command: The kubectl command to execute (e.g. 'get pods', 'describe deployment nginx')
    """
    try:
        # make a subprocess.run call to execute shell commands
        result = subprocess.run(
            ["kubectl"] + command.split(), capture_output=True, text=True
        )
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error executing kubectl command: {str(e)}"


@tool
def helm_exec(command: str) -> str:
    """A tool that executes Helm commands.

    Args:
        command: The helm command to execute (e.g. 'list', 'install myapp ./chart')
    """
    try:
        # make a subprocess.run call to execute shell commands
        result = subprocess.run(
            ["helm"] + command.split(), capture_output=True, text=True
        )
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error executing helm command: {str(e)}"


@tool
def docker_exec(command: str) -> str:
    """A tool that executes docker commands.

    Args:
        command: The docker command to execute (e.g. 'ps', 'images', 'build -t myapp .')
    """
    try:
        # make a subprocess.run call to execute shell commands
        result = subprocess.run(
            ["docker"] + command.split(), capture_output=True, text=True
        )
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error executing docker command: {str(e)}"


@tool
def git_exec(command: str) -> str:
    """A tool that executes git commands.

    Args:
        command: The git command to execute (e.g. 'status', 'pull origin main')
    """

    try:
        # make a subprocess.run call to execute shell commands
        result = subprocess.run(
            ["git"] + command.split(), capture_output=True, text=True
        )

        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error executing git command: {str(e)}"


@tool
def file_manage(operation: str, path: str, content: str = None) -> str:
    """Perform file operations.

    Args:
        operation: The operation to perform ('read', 'write', 'delete', 'list')
        path: Path to the file or directory
        content: Content to write (only for 'write' operation)
    """
    try:
        # conditional file operations
        if operation == "read":
            with open(path, "r") as f:
                return f.read()
        elif operation == "write":
            with open(path, "w") as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        elif operation == "delete":
            os.remove(path)
            return f"Successfully deleted {path}"
        elif operation == "list":
            return "\n".join(os.listdir(path))
        else:
            return "Invalid operation. Use 'read', 'write', 'delete', or 'list'"
    except Exception as e:
        return f"Error performing file operation: {str(e)}"


@tool
def gcloud_exec(command: str) -> str:
    """A tool that executes gcloud commands.

    Args:
        command: The gcloud command to execute (e.g. 'compute instances list', 'config set project my-project')
    """
    try:
        # make a subprocess.run call to execute shell commands
        result = subprocess.run(
            ["gcloud"] + command.split(), capture_output=True, text=True
        )
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error executing gcloud command: {str(e)}"


@tool
def docker_retrieval(query: str) -> str:
    """Tuning to Docker Best Practices.
    Search and return information about Docker related topics on devops operations
    eg: for creating a docker file, building a docker image, running a docker container, etc.


    Args:
        state (dict): The current graph state
        Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    try:
        retriever = vectorstore_devops(
            docker_rag.get("collection_name"), docker_rag.get("kwargs")
        )
        documents = retriever.invoke(query)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
            for doc in documents
        )
        return serialized
    except Exception as e:
        return f"Error retrieving Docker documents: {str(e)}"


@tool
def bq_retrieval(query: str) -> str:
    """Tuning to BigQuery Best Practices.
    Search and return information about BigQuery related topics on devops operations
    eg: for creating a bigquery table, querying a bigquery table, etc.

    Args:
        query: The query to search for
    """
    try:
        retriever = vectorstore_devops(
            bq_rag.get("collection_name"), bq_rag.get("kwargs")
        )
        documents = retriever.invoke(query)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
            for doc in documents
        )
        return serialized
    except Exception as e:
        return f"Error retrieving BigQuery documents: {str(e)}"


@tool
def gsutil_exec(command: str) -> str:
    """A tool that executes gsutil commands.

    Args:
        command: The gsutil command to execute (e.g. 'ls gs://my-bucket', 'cp file gs://my-bucket')
    """
    try:
        result = subprocess.run(
            ["gsutil"] + command.split(), capture_output=True, text=True
        )
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error executing gsutil command: {str(e)}"


@tool
def bq_exec(command: str) -> str:
    """A tool that executes bq commands for interacting with GCP BigQuery.

    Args:
        command: The bq command to execute (e.g. "query --use_legacy_sql=false 'SELECT * FROM my_dataset.my_table'")
    """
    try:
        # Use shlex.split to parse the command correctly
        args = ["bq"] + shlex.split(command)
        result = subprocess.run(args, capture_output=True, text=True)
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error executing bq command: {str(e)}"


@tool
def jira_info(query: str) -> str:
    """Jira Issues.
    Search and return information about Jira related topics

    Args:
        state (dict): The current graph state
        Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    try:
        jira = JiraAPIWrapper()
        toolkit = JiraToolkit.from_jira_api_wrapper(jira)
        agent = initialize_agent(
            toolkit.get_tools(),
            llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
        )

        result = agent.run(query)
        return result
    except Exception as e:
        return f"Error retrieving Jira Info: {str(e)}"


@tool
def confluence_retrieval(query: str) -> str:
    """Extracting Confluence docs.
    Search and return information all about the Confluence space and its pages

    Args:
        query: The query to search for

    """
    try:

        retriever = vectorstore_devops(
            confluence_rag.get("collection_name"), confluence_rag.get("kwargs")
        )
        documents = retriever.invoke(query)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
            for doc in documents
        )
        return serialized
    except Exception as e:
        return f"Error retrieving confluence documents: {str(e)}"


# AWS and Azure CLI tools
@tool
def aws_retrieval(query: str) -> str:
    """A tool that retrieves AWS documents.

    Args:
        query: The query to search for
    """
    try:
        retriever = vectorstore_devops(
            aws_rag.get("collection_name"), aws_rag.get("kwargs")
        )
        documents = retriever.invoke(query)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
            for doc in documents
        )
        return serialized
    except Exception as e:
        return f"Error retrieving AWS documents: {str(e)}"


@tool
def aws_exec(command: str) -> str:
    """A tool that executes aws commands. Always use local aws credentials and config at ~/.aws/credentials and ~/.aws/config before using this tool.

    Fetch account info first to ensure the command is executed with the correct credentials.

    Args:
        command: The aws command to execute (e.g. 'ec2 describe-instances' or 's3 ls' or 'ecs list-clusters' or 'eks list-clusters')
    """
    logger.warning(f"Executing aws command: {command}")
    try:
        # run a command to fetch account info first
        check_account_info = subprocess.run(
            ["aws", "sts", "get-caller-identity"], capture_output=True, text=True
        )

        # check if the account info is fetched successfully
        if check_account_info.returncode != 0:
            return f"Error fetching account info: {check_account_info.stderr}"

        # log the account info
        logger.debug(check_account_info.stdout)

        # make a subprocess.run call to execute shell commands
        result = subprocess.run(
            ["aws"] + command.split(), capture_output=True, text=True
        )
        return result.stdout if result.stdout else result.stderr

    except Exception as e:
        return f"Error executing aws command: {str(e)}"


@tool
def azure_exec(command: str) -> str:
    """A tool that executes azure commands.

    Args:
        command: The azure command to execute (e.g. 'login' or 'vm list' or 'group list' or 'aks list')
    """

    try:
        # check for azure profile
        profile = os.getenv("AZURE_CLIENT_ID")
        if profile:
            # login with cliend ID
            subprocess.run(["az", "login", "--identity", "--username", profile])
            # make a subprocess.run call to execute shell commands
            result = subprocess.run(
                ["az"] + command.split(), capture_output=True, text=True
            )
            return result.stdout if result.stdout else result.stderr
        else:
            raise ValueError("AZURE_CLIENT_ID environment variable not set")
    except Exception as e:
        return f"Error executing azure command: {str(e)}"
