import logging

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    CustomerServiceAgent,
    ReplyAgent,
    SupervisorAgent,
    TechnicalAssistantAgent,
    TextCustomerServiceAgent,
)
from app.agents.state import AftercareState
from app.mcp.client import AftercareMcpClient


class AftercareWorkflow:
    """Builds and runs the supervisor-routed LangGraph workflow."""

    def __init__(self, mcp_client: AftercareMcpClient | None = None) -> None:
        self.mcp_client = mcp_client or AftercareMcpClient()
        self.graph = self.build_graph()

    def build_graph(self):
        """Wire the agent nodes in the order required by the business flow."""

        graph = StateGraph(AftercareState)
        graph.add_node("supervisor", SupervisorAgent())
        graph.add_node("image_customer_service", CustomerServiceAgent(self.mcp_client))
        graph.add_node("text_customer_service", TextCustomerServiceAgent(self.mcp_client))
        graph.add_node("technical_assistant", TechnicalAssistantAgent(self.mcp_client))
        graph.add_node("reply_agent", ReplyAgent(self.mcp_client))

        graph.set_entry_point("supervisor")
        graph.add_conditional_edges(
            "supervisor",
            self.route_after_supervisor,
            {
                "image_intake": "image_customer_service",
                "text_intake": "text_customer_service",
            },
        )
        graph.add_edge("image_customer_service", "technical_assistant")
        graph.add_edge("text_customer_service", "technical_assistant")
        graph.add_edge("technical_assistant", "reply_agent")
        graph.add_edge("reply_agent", END)

        return graph.compile()

    def route_after_supervisor(self, state: AftercareState) -> str:
        """Return the next node key selected by the supervisor."""

        return state["intake_route"]

    async def run(
        self,
        customer_email: str,
        description: str,
        image_filename: str = "",
        image_content_type: str = "application/octet-stream",
        image_bytes: bytes = b"",
    ) -> AftercareState:
        """Create the initial graph state and run the workflow."""

        logging.info(
            "workflow | started customer_email=%s image=%s bytes=%s",
            customer_email,
            image_filename,
            len(image_bytes),
        )
        final_state = await self.graph.ainvoke(
            {
                "customer_email": customer_email,
                "description": description,
                "image_filename": image_filename,
                "image_content_type": image_content_type,
                "image_bytes": image_bytes,
            }
        )
        logging.info(
            "workflow | finished ticket_id=%s status=%s",
            final_state.get("ticket_id"),
            final_state.get("status"),
        )
        return final_state


aftercare_workflow = AftercareWorkflow()

# Compatibility name for older imports.
aftercare_graph = aftercare_workflow.graph
