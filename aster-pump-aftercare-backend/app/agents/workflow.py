import logging

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    CustomerServiceAgent,
    ModelPlannerAgent,
    PlanValidatorAgent,
    ReplyAgent,
    TechnicalAssistantAgent,
    TextCustomerServiceAgent,
)
from app.agents.state import AftercareState
from app.mcp.client import AftercareMcpClient


class AftercareWorkflow:
    """Builds and runs the model-planned LangGraph workflow."""

    def __init__(self, mcp_client: AftercareMcpClient | None = None) -> None:
        self.mcp_client = mcp_client or AftercareMcpClient()
        self.graph = self.build_graph()

    def build_graph(self):
        """Wire the agent nodes in the order required by the business flow."""

        graph = StateGraph(AftercareState)
        graph.add_node("model_planner", ModelPlannerAgent())
        graph.add_node("plan_validator", PlanValidatorAgent())
        graph.add_node("image_customer_service", CustomerServiceAgent(self.mcp_client))
        graph.add_node("text_customer_service", TextCustomerServiceAgent(self.mcp_client))
        graph.add_node("technical_assistant", TechnicalAssistantAgent(self.mcp_client))
        graph.add_node("reply_agent", ReplyAgent(self.mcp_client))

        graph.set_entry_point("model_planner")
        graph.add_edge("model_planner", "plan_validator")
        graph.add_conditional_edges(
            "plan_validator",
            self.route_after_plan_validator,
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

    def route_after_plan_validator(self, state: AftercareState) -> str:
        """Return the next node key approved by the plan validator."""

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
                "workflow_step_count": 0,
                "supervisor_route_count": 0,
                "workflow_trace": [],
            }
        )
        logging.info(
            "workflow | finished ticket_id=%s status=%s steps=%s trace=%s",
            final_state.get("ticket_id"),
            final_state.get("status"),
            final_state.get("workflow_step_count"),
            final_state.get("workflow_trace"),
        )
        return final_state


aftercare_workflow = AftercareWorkflow()

# Compatibility name for older imports.
aftercare_graph = aftercare_workflow.graph
