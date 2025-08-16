import sys
import os
from typing import Dict, Any, Literal
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from langgraph.graph import StateGraph, END
from agents.graph_state import GraphState
from agents.tracey_agent import TraceyAgent 
from tools.plaid_tool import PlaidTool
from tools.research_tool import ResearchTool
from tools.categorization_tool import SemanticCategorizer
from tools.budget_optimizer import BudgetOptimizer

load_dotenv()

class FinancialGuardianSystem:
    def __init__(self):
        print("🤖 Initializing Financial Agent System...")
        self.agent = TraceyAgent(groq_api_key=os.getenv("GROQ_API_KEY"))
        
        # initialize tools
        self.plaid_tool = PlaidTool()
        self.categorizer = SemanticCategorizer()
        self.budget_optimizer = BudgetOptimizer()
        
        tavily_key = os.getenv("TAVILY_API_KEY")
        self.research_tool = ResearchTool(tavily_key) if tavily_key else None
        
        self.app = self._build_graph()
        print("✅ Financial Agent System ready!")
    
    def _build_graph(self):
        workflow = StateGraph(GraphState)
        
        # add nodes
        workflow.add_node("agent", self.autonomous_agent_wrapper)
        workflow.add_node("tool_node", self.enhanced_tool_node)
        
        # set entry point
        workflow.set_entry_point("agent")
        
        # add conditional routing
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {"tool_node": "tool_node", END: END}
        )
        
        # loop back from tools to agent for continued reasoning
        workflow.add_edge("tool_node", "agent")
        
        return workflow.compile(debug=True)
    
    def autonomous_agent_wrapper(self, state: GraphState) -> GraphState:
        print(f"\n🧠 Agent Reasoning (Step {state.get('current_step', 0) + 1})")
        
        current_step = state.get("current_step", 0)
        if current_step >= 10:  # limit to prevent infinity loops
            print("   - Safety: Maximum exploration reached")
            return self.agent._generate_final_response(state, "Comprehensive analysis completed")
        
        # check for tool repetition patterns
        recent_tools = [result.get("tool", "") for result in state.get("tool_results", [])[-3:]]
        if len(recent_tools) >= 2 and len(set(recent_tools)) <= 1:
            print(f"   - Safety: Tool repetition detected, ending analysis")
            return self.agent._generate_final_response(state, "Analysis complete - prevented infinite loop")
        
        return self.agent.agent_node(state)
    
    def enhanced_tool_node(self, state: GraphState) -> GraphState:
        updated_state = state.copy()
        tool_calls = state.get("tool_calls", [])
        
        if not tool_calls:
            return updated_state
        
        if updated_state.get("tool_results") is None:
            updated_state["tool_results"] = []
        
        for call in tool_calls:
            tool_name = call.get("tool")
            args = call.get("args", {})
            
            print(f"    🔧 Executing: {tool_name}")
            
            try:
                tool_output = self._execute_tool(tool_name, args, state)
                updated_state = self._update_state_with_tool_result(
                    updated_state, tool_name, tool_output
                )
                updated_state["tool_results"].append(tool_output)
                
            except Exception as e:
                error_output = {"error": f"Tool {tool_name} failed: {str(e)}"}
                updated_state["tool_results"].append(error_output)
                print(f"Tool Error: {e}")
        
        # clear tool calls for next iteration
        updated_state["tool_calls"] = []
        return updated_state
    
    def _execute_tool(self, tool_name: str, args: Dict, state: GraphState) -> Dict[str, Any]:
        if tool_name == "get_transactions":
            transactions = self.plaid_tool.get_transactions()
            return {
                "tool": "get_transactions",
                "transactions_retrieved": len(transactions),
                "transactions": transactions
            }
        
        elif tool_name == "categorize_transactions":
            categorized_txns = self.categorizer.run(state['transactions'])
            return {
                "tool": "categorize_transactions",
                "transactions_categorized": len(categorized_txns),
                "categorized_transactions": categorized_txns
            }
        
        elif tool_name == "analyze_spending":
            analysis = self.plaid_tool.analyze_spending(
                state['transactions'], 
                state['budget']
            )
            return {
                "tool": "analyze_spending",
                "analysis_type": "spending_analysis",
                **analysis
            }
        
        elif tool_name == "research_tips":
            return self._execute_autonomous_research(args, state)
        
        elif tool_name == "optimize_budget":
            optimization = self.budget_optimizer.analyze_and_optimize(
                current_budget=state['budget'],
                baseline_spending=args.get("baseline_spending", {}),
                new_transactions=args.get("new_transactions", {}),
                transactions=state['transactions']
            )
            return {
                "tool": "optimize_budget",
                **optimization
            }
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _execute_autonomous_research(self, args: Dict, state: GraphState) -> Dict[str, Any]:
        if not self.research_tool:
            return {"error": "Research tool not available"}
        
        # agent can specify research parameters
        topic = args.get("topic", "financial optimization")
        category = args.get("category", "general")
        
        # extract context for better research
        user_context = state.get("user_context", {})
        location = user_context.get("location", "general")
        
        # calculate relevant financial context from detected deviations
        budget_deficit = 0
        transaction_details = None
        research_category = "general"
        
        # use the actual deviation details for targeted research
        deviation_details = state.get("deviation_details", {})
        if deviation_details:
            # find the category with the highest overage for research
            max_overage_category = max(deviation_details.items(), 
                                     key=lambda x: x[1].get('overage', 0))
            research_category = max_overage_category[0] 
            budget_deficit = max_overage_category[1].get('overage', 0)
            transaction_details = max_overage_category[1]
            
            print(f"   - Research target: {research_category} (RM{budget_deficit:.0f} overage)")
            print(f"   - Sample transactions: {[t.get('description', '') for t in transaction_details.get('transaction_details', [])[:2]]}")
        
        return self.research_tool.search_cost_saving_tips(
            topic=f"{research_category.lower()} overspending",  # more specific topic
            category=research_category,  # use the actual overspent category
            location=location, 
            budget_deficit=budget_deficit, 
            transaction_details=transaction_details
        )
    
    def _update_state_with_tool_result(self, state: GraphState, tool_name: str, result: Dict) -> GraphState:
        if tool_name == "get_transactions" and "transactions" in result:
            state["transactions"] = result["transactions"]
        
        elif tool_name == "categorize_transactions" and "categorized_transactions" in result:
            state["transactions"] = result["categorized_transactions"]
        
        elif tool_name == "analyze_spending":
            state["deviation_detected"] = result.get("deviation_detected", False)
            state["deviation_details"] = result.get("deviation_details", {})
            state["spending_analysis"] = result
        
        elif tool_name == "optimize_budget" and result.get("proposed_budget"):
            state["proposed_budget"] = result["proposed_budget"]
            state["budget_optimization"] = result
        
        return state
    
    def _should_continue(self, state: GraphState) -> Literal["tool_node", "__end__"]:
        if state.get("tool_calls"):
            return "tool_node"
        return END
    
    def create_initial_state(self, user_context: Dict, budget: Dict) -> GraphState:
        return {
            "user_context": user_context,
            "budget": budget,
            "transactions": [],
            "messages": [{"role": "user", "content": "Please analyze my financial situation"}],
            "tool_results": [],
            "current_step": 0,
            "max_steps": 10,  # Allow more exploration
            "deviation_detected": False,
            "deviation_details": {},
            "research_queries": [],
            "tool_calls": [],
            "recovery_recommendations": [],
            "budget_status": "unknown"
        }
    
    def run_analysis(self, user_context: Dict, budget: Dict):
        initial_state = self.create_initial_state(user_context, budget)
        
        print("Starting Autonomous Financial Analysis...")
        print(f"User: {user_context.get('name', 'Unknown')}")
        print(f"Location: {user_context.get('location', 'Unknown')}")
        print(f"Budget Categories: {list(budget.keys())}")
        
        for output in self.app.stream(initial_state, {"recursion_limit": 20}):
            yield output
