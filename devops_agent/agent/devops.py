import os
from typing import Dict, List, Literal, Union, cast

from copilotkit.langchain import copilotkit_customize_config, copilotkit_emit_state
from devops_agent.config.devops import CustomNodeConfig
from devops_agent.data.devops_prompt import SYSTEM_PROMPT
from devops_agent.logs.logging import logger
from devops_agent.states.devops import AgentState
from devops_agent.tools.devops import (
    aws_exec,
    azure_exec,
    bq_exec,
    bq_retrieval,
    confluence_retrieval,
    docker_exec,
    docker_retrieval,
    file_manage,
    gcloud_exec,
    git_exec,
    gsutil_exec,
    helm_exec,
    jira_info,
    kubectl_exec,
)
from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

load_dotenv(os.path.join(os.getcwd(), ".env"))

# Default number of messages to keep in history before summarizing
DEFAULT_MESSAGE_HISTORY_LIMIT = 25

# Default number of messages to keep in history after summarizing
DEFAULT_MESSAGE_HISTORY_LIMIT_AFTER_SUMMARY = 10


class DevOpsAgent:
    """A Langgraph agent that performs DevOps tasks using tools."""

    def __init__(self):
        self.summary_threshold = int(
            os.getenv("MESSAGE_HISTORY_LIMIT", DEFAULT_MESSAGE_HISTORY_LIMIT)
        )
        self.summary_threshold_after_summary = int(
            os.getenv(
                "MESSAGE_HISTORY_LIMIT_AFTER_SUMMARY",
                DEFAULT_MESSAGE_HISTORY_LIMIT_AFTER_SUMMARY,
            )
        )

        # set tools
        self.tools_list = [
            kubectl_exec,
            docker_exec,
            git_exec,
            file_manage,
            helm_exec,
            gcloud_exec,
            docker_retrieval,
            gsutil_exec,
            bq_exec,
            bq_retrieval,
            jira_info,
            confluence_retrieval,
            aws_exec,
            azure_exec,
        ]
        self.ragtool_list = ["docker_retrieval", "bq_retrieval", "confluence_retrieval"]
        self.tools = {
            "kubectl_exec": kubectl_exec,
            "docker_exec": docker_exec,
            "git_exec": git_exec,
            "file_manage": file_manage,
            "helm_exec": helm_exec,
            "gcloud_exec": gcloud_exec,
            "docker_retrieval": docker_retrieval,
            "gsutil_exec": gsutil_exec,
            "bq_exec": bq_exec,
            "bq_retrieval": bq_retrieval,
            "jira_info": jira_info,
            "confluence_retrieval": confluence_retrieval,
            "aws_exec": aws_exec,
            "azure_exec": azure_exec,
        }
        self.tools_description = {
            "kubectl_exec": "Execute Kubernetes commands",
            "docker_exec": "Execute Docker commands",
            "git_exec": "Execute Git commands",
            "file_manage": "Perform File Manage operations",
            "helm_exec": "Execute Helm commands",
            "gcloud_exec": "Execute Google Cloud commands",
            "docker_retrieval": "Tuning to Docker Best Practices",
            "jira_info": "Get information from Jira",
            "bq_exec": "Execute BigQuery commands",
            "bq_retrieval": "Tuning to BigQuery Knowledge Base",
            "confluence_retrieval": "Loading Confluence Information",
            "aws_exec": "Execute AWS commands with local aws credentials and config at ~/.aws/credentials and ~/.aws/config",
            "azure_exec": "Execute Azure commands",
        }

        # set tools requiring approval
        self.tools_requiring_approval = {
            "kubectl_exec": ["create", "delete", "apply", "patch", "scale"],
            "docker_exec": ["build", "create", "run", "rm", "rmi"],
            "git_exec": ["clone", "push", "commit", "merge", "branch", "tag"],
            "helm_exec": ["install", "uninstall", "upgrade", "rollback"],
            "file_manage": ["read", "list", "write", "create", "delete", "modify"],
            "gcloud_exec": [],
            "gsutil_exec": [],
            "bq_exec": [],
            "aws_exec": [],
            "azure_exec": [],
        }

        # define LLM
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,  # , base_url="https://openrouter.ai/api/v1"
        )

        # bind tools with LLM
        self.llmtools = self.model.bind_tools(
            self.tools_list, parallel_tool_calls=False
        )

        # set logger, memory and builder
        self.logger = logger
        self.builder = StateGraph(AgentState)
        self.memory = MemorySaver()

        # build graph
        self.graph = None

    def requires_human_approval(
        self, tool_name: str, tool_args: str, auto_approve
    ) -> bool:
        """A method that returns operation or command for human approval.

        Args:
            tool_name (str): Name of the tool.
            args (dict): Arguments to pass to commands.

        Returns:
            bool: check for whether or not to proceed.
        """

        # check for tool name and arguments
        return (
            auto_approve == AgentState.AutoApprove.NO.value
            and tool_name in self.tools_requiring_approval
        )

    async def human_node(
        self, state: AgentState, config: CustomNodeConfig
    ):  # pylint: disable=unusued-argument
        """A method that returns state as is from human (used to interrupt chat process) node with LLM.

        Args:
            state (AgentState): The state of the agent.
            config (CustomNodeConfig): Custom config used for invocation of LLMs."""

        # log the state
        logger.debug("Human Node State: {}".format(state.__str__()))
        return state

    async def assistant(
        self, state: AgentState, config: CustomNodeConfig
    ) -> Dict[str, List[Union[HumanMessage, AIMessage, SystemMessage]]]:
        """A method that invokes assistant (main agent) node with LLM.

        Args:
            state (AgentState): The state of the agent.
            config (CustomNodeConfig): Custom config used for invocation of LLMs."""

        summary = state.get("summary", "")

        if summary:
            logger.info("Summary present. Adding summary to messages.")
            system_message = f"Summary of conversation earlier: {summary}"
            messages = [SystemMessage(content=system_message)] + state["messages"]
        else:
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

        # messages = [SystemMessage(content=SYSTEM_PROMPT)] + state.get("messages")
        state["logs"] = state.get("logs", [])
        state["devopsSuggestions"] = state.get("devopsSuggestions", [])
        state["auto_approve"] = state.get("auto_approve", AgentState.AutoApprove.NO)

        # log the state
        logger.debug("Assistant Node State: {}".format(state.__str__()))

        # emit current state
        await copilotkit_emit_state(config, state)
        # set custom config
        if state["auto_approve"] == "no":

            config = copilotkit_customize_config(
                config,
                emit_tool_calls=[
                    "git_exec",
                    "file_manage",
                    "docker_exec",
                    "gcloud_exec",
                    "helm_exec",
                    "kubectl_exec",
                    "aws_exec",
                    "azure_exec",
                ],
            )
        else:

            config = copilotkit_customize_config(config, emit_tool_calls=False)

        response = await self.llmtools.ainvoke(messages, config)

        return {"messages": [response]}

    async def human_review_node(
        self, state: AgentState, config: CustomNodeConfig
    ) -> Command[Literal["assistant", "run_tool", END]]:
        """A method that invokes human review (decider node between assistant and run_tool after human gives input) node with LLM.

        Args:
            state (AgentState): The state of the agent.
            config (CustomNodeConfig): Custom config used for invocation of LLMs.
        """

        # fetch last message
        __last_message = state["messages"][-2]
        logger.debug("Human Review Node Last Message: ", __last_message)

        # log the state
        logger.debug("Human Review Node State: {}".format(state))

        # check if the list of messages has tool calls
        if hasattr(state.get("messages")[-1], "tool_calls"):
            _tool_calls = state.get("messages")[-1].tool_calls
            _tool_call = _tool_calls[0]
            logger.debug("Human Review Node Last Tool call: ", _tool_call)

        # chekc if the last message was a tool message
        elif hasattr(__last_message, "tool_calls") and isinstance(
            state["messages"][-1], ToolMessage
        ):
            _tool_calls = __last_message.tool_calls
            _tool_call = _tool_calls[0]
            _tool_message = cast(ToolMessage, state["messages"][-1])
            logger.debug("Human Review Node Last Tool call: ", _tool_call)

        # if approved by human
        if _tool_message.content == "YES":
            logger.debug("Human Review Node Approve Message: ", _tool_message.content)
            await copilotkit_emit_state(config, state)
            return Command(goto="run_tool")

        # if denied by human
        elif _tool_message.content == "NO":

            logger.debug("Human Review Node Deny Message: ", _tool_message.content)

            # set command with arguments
            state["logs"] = state.get("logs", [])
            command = _tool_call["args"]
            state["logs"].append(
                {"message": "Aborted cmd", "command": command, "done": True}
            )

            # emit the current state
            await copilotkit_emit_state(config, state)

            # set last tool message
            last_tool_message = state["messages"].pop()
            last_tool_message = cast(ToolMessage, last_tool_message)
            last_tool_message.content = "NO"
            logger.debug("Human Review Node Last Tool message: ", last_tool_message)

            # return command goto
            new_messages = [last_tool_message]
            await copilotkit_emit_state(config, state)
            return Command(goto=END, update={"messages": new_messages})

    async def run_tool(self, state: AgentState, config: CustomNodeConfig) -> Dict:
        """A method that invokes run tool (the tool that invokes other tools) node with LLM.

        Args:
            state (AgentState): The state of the agent.
            config (CustomNodeConfig): Custom config used for invocation of LLMs."""

        # set new messages and tools
        new_messages = []
        tools = self.tools

        # check for last tool calls
        if hasattr(state.get("messages")[-1], "tool_calls"):
            _tool_calls = state.get("messages")[-1].tool_calls
        elif hasattr(state.get("messages")[-2], "tool_calls") and isinstance(
            state.get("messages")[-1], ToolMessage
        ):
            _tool_calls = state.get("messages")[-2].tool_calls

        # loop over the tool calls to execute the tools
        for toolcall in _tool_calls:
            tool = tools[toolcall["name"]]

            # fetch state logs
            state["logs"] = state.get("logs", [])
            logs_offset = len(state["logs"])
            __command = toolcall["args"]
            description = self.tools_description.get(toolcall["name"], "Tool ")
            state["logs"].append(
                {
                    "message": f"running command {tool}",
                    "command": __command,
                    "done": False,
                    "result": "",
                    "description": description,
                }
            )

            # emit current state
            await copilotkit_emit_state(config, state)

            # extract result of the tool
            result = await tool.ainvoke(toolcall["args"])

            logger.debug("Run Tool Node Tool result: ", result)
            logger.debug(
                "Run Tool Node State config values: {}".format(state.__str__())
            )

            # set log status with offset to true
            if toolcall["name"] in self.ragtool_list:
                summary_message = "Create a summary of the documentation above:"
                messages = [result] + [HumanMessage(content=summary_message)]
                response = await self.model.ainvoke(messages)
                result = response.content
                state["logs"][logs_offset]["result"] = result
            else:
                state["logs"][logs_offset]["result"] = result

            state["logs"][logs_offset]["done"] = True

            # emit current state
            await copilotkit_emit_state(config, state)

            logger.debug(
                "Run Tool Node Result: ",
                state.get("messages")[-1],
                "second",
                state.get("messages")[-2],
            )

            # set last tool messages
            last_tool_message = None
            if hasattr(state.get("messages")[-2], "tool_calls") and isinstance(
                state.get("messages")[-1], ToolMessage
            ):
                logger.debug("Current state messages: ", state["messages"])

                # set value to last tool message to last tool message
                last_tool_message = state["messages"].pop()
                last_tool_message = cast(ToolMessage, last_tool_message)
                logger.debug(
                    "State messages after last message assignment: ", state["messages"]
                )

            # set last tool message with tool result
            if last_tool_message:
                last_tool_message.content = result
                new_messages.append(last_tool_message)
                return {"messages": new_messages}

            if hasattr(state.get("messages")[-1], "tool_calls") and isinstance(
                state.get("messages")[-1], AIMessage
            ):
                message_to_append = {
                    "role": "tool",
                    "name": toolcall["name"],
                    "content": result,
                    "tool_call_id": toolcall["id"],
                }
                new_messages.append(message_to_append)
                logger.debug("State messages to append: ", message_to_append)
                return {"messages": new_messages}

    async def route_after_assistant(
        self, state: AgentState, config: CustomNodeConfig
    ) -> Literal[END, "human_node", "run_tool", "summarize_conversation"]:
        """A method that invokes route after assistant (the tool that routes to appropriate node based on tool calls) node with LLM.

        Args:
            state (AgentState): The state of the agent.
            config (CustomNodeConfig): Custom config used for invocation of LLMs."""

        messages = state.get("messages")
        if len(messages) > self.summary_threshold and (
            (
                not hasattr(messages[-1], "tool_calls")
                or len(messages[-1].tool_calls) == 0
            )
            and (
                not hasattr(messages[-2], "tool_calls")
                or len(messages[-2].tool_calls) == 0
            )
        ):
            logger.debug("ABOUT TO SUMMARIZE CONVERSATION")
            return "summarize_conversation"

        # check for last message in state
        __last_message = state.get("messages")[-1]
        if (
            not hasattr(__last_message, "tool_calls")
            or len(__last_message.tool_calls) == 0
        ):
            return END

        # for all tool calls, route to human/run based tool nodes
        for toolcall in __last_message.tool_calls:

            logger.debug("Tool call: ", toolcall["name"])

            if self.requires_human_approval(
                toolcall["name"], toolcall["args"], state["auto_approve"]
            ):
                logger.debug("State auto approve: ", state["auto_approve"])
                return "human_node"

        return "run_tool"

    async def route_after_summarize_conversation(
        self, state: AgentState, config: CustomNodeConfig
    ) -> Literal[END, "human_node", "run_tool"]:
        """Route to appropriate node based on tool calls and required approvals"""

        last_message = state["messages"][-1]
        if not hasattr(last_message, "tool_calls") or len(last_message.tool_calls) == 0:
            await copilotkit_emit_state(config, state)
            return END

        for tool_call in last_message.tool_calls:
            await copilotkit_emit_state(config, state)
            if self.requires_human_approval(
                tool_call["name"], tool_call["args"], state["auto_approve"]
            ):
                return "human_node"

        return "run_tool"

    async def summarize_conversation(self, state: AgentState, config: CustomNodeConfig):
        logger.info("INSIDE SUMMARIZE NODE")
        summary = state.get("summary", "")
        if summary:
            # If a summary already exists, extend it
            summary_message = (
                f"This is summary of the conversation to date: {summary}\n\n"
                "Extend the summary by taking into account the new messages above:"
            )
        else:
            # Create a new summary
            summary_message = "Create a summary of the conversation above:"

        # Combine existing messages with the summary prompt
        messages = state.get("messages") + [HumanMessage(content=summary_message)]

        # Invoke the language model to generate the summary
        response = await self.model.ainvoke(messages)

        # Determine how many messages to keep based on the message history limit after summary
        messages_to_keep = self.summary_threshold_after_summary

        if len(state["messages"]) >= messages_to_keep and isinstance(
            state["messages"][-messages_to_keep], ToolMessage
        ):
            # Keep one extra message if the second-to-last is a ToolMessage
            messages_to_keep += 1

        # Create list of messages to delete, keeping the last few messages
        delete_messages = [
            RemoveMessage(id=m.id)
            for m in state["messages"][:-messages_to_keep]
            if m.id is not None
        ]

        logger.info("Deleting messages: {}", delete_messages)

        return {"summary": response.content, "messages": delete_messages}

    async def build_graph(self, checkpointer):
        """A method that builds graph."""

        builder = self.builder

        # add nodes
        builder.add_node("assistant", self.assistant)
        builder.add_node("human_node", self.human_node)
        builder.add_node("human_review_node", self.human_review_node)
        builder.add_node("run_tool", self.run_tool)

        builder.add_node("summarize_conversation", self.summarize_conversation)

        # add edges
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant",
            self.route_after_assistant,
        )
        builder.add_edge("human_node", "human_review_node")
        builder.add_edge("human_review_node", END)
        builder.add_edge("assistant", END)
        builder.add_edge("run_tool", "assistant")

        builder.add_conditional_edges(
            "summarize_conversation", self.route_after_summarize_conversation
        )

        # compile graph
        return builder.compile(
            checkpointer=checkpointer, interrupt_after=["human_node"]
        )
