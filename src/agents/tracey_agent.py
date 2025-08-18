from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage
from agents.graph_state import GraphState
import json
import re
import time

class TraceyAgent:
    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-70b-8192",
            temperature=0.1 
        )
        self.reasoning_history = []
    
    def _is_analysis_complete(self, state: GraphState) -> bool:
        tools_run = {result.get("tool") for result in state.get("tool_results", []) if result.get("tool")}
        deviation_detected = state.get("deviation_detected", False)
        current_step = state.get("current_step", 0)
        
        print(f"  🔍 COMPLETION CHECK - Step {current_step}:")
        print(f"    Tools run so far: {tools_run}")
        print(f"    Deviation detected: {deviation_detected}")

        # Always need spending analysis first
        if "analyze_spending" not in tools_run:
            print(f"    ❌ Not complete: analyze_spending not run")
            return False

        # If no deviation, we're done after analysis
        if not deviation_detected:
            print(f"    ✅ Complete: No deviations detected")
            return True
        
        # If deviation detected, we need optimization attempts and research
        has_optimization = "optimize_budget" in tools_run
        has_research = "research_tips" in tools_run
        
        print(f"    Optimization attempted: {has_optimization}")
        print(f"    Research completed: {has_research}")
        
        # check for duplicate tool calls in recent steps to prevent loops
        recent_tools = [result.get("tool") for result in state.get("tool_results", [])[-4:]]
        tool_counts = {}
        for tool in recent_tools:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        # if we've run the same tool more than twice recently, force completion
        for tool, count in tool_counts.items():
            if count >= 2:
                print(f"    ✅ Complete: Detected tool repetition ({tool} run {count} times)")
                return True
        
        # For deviations: we need BOTH optimization attempt AND research
        if has_optimization and has_research:
            print(f"    ✅ Complete: Both optimization and research completed")
            return True
            
        # Safety: If we've done too many steps, force completion
        if current_step >= 8:  # Reduced from 10 to prevent infinite loops
            print(f"    ⚠️ Complete: Safety limit reached at step {current_step}")
            return True
            
        print(f"    ⏳ Not complete: Need optimization({has_optimization}) and research({has_research})")
        return False
    
    def agent_node(self, state: GraphState) -> GraphState:
        current_step = state.get("current_step", 0)
        
        # Check if analysis is complete according to SOP
        if self._is_analysis_complete(state):
            print("🧠 Agent: SOP complete. Generating final response.")
            # Generate final response and preserve state
            final_response_updates = self._generate_final_response(state, "Analysis completed successfully")
            
            # --- PRESERVE ALL STATE ROBUSTLY ---
            final_state = state.copy()  # Start with complete copy
            final_state.update(final_response_updates)  # Add final response
            
            
            return final_state
        
        # safety check to avoid infinity loops, max steps = 10
        if current_step >= 10:
            print("   - Agent: Reached step limit, providing final analysis")
            final_response_updates = self._generate_final_response(state, "Analysis completed after thorough investigation")
            
            # Preserve state and add final response
            final_state = state.copy()
            final_state.update(final_response_updates)
            
            return final_state
        
        # log reasoning step
        reasoning_step = f"Step {current_step + 1}: Analyzing financial state"
        self.reasoning_history.append(reasoning_step)
        print(f"   - Agent Reasoning: {reasoning_step}")
        
        try:
            # LLM analyze the state and decide what to do next
            system_prompt = self._build_autonomous_system_prompt()
            messages = self._format_analysis_context(state)
            
            response = self.llm.invoke([system_prompt] + messages)
            response_content = response.content.strip()
            
            # standardize output
            parsed_response = self._parse_agent_decision(response_content)
            final_state = state.copy()  
            if parsed_response.get("needs_tool"):
                # agent decided it needs more information
                tool_call = parsed_response["tool_call"]
                final_state["tool_calls"] = [tool_call]
                final_state["current_analysis"] = parsed_response.get("reasoning", "Gathering additional data")
                print(f"   - Agent Decision: {parsed_response['reasoning']}")
                print(f"   - Tool Selected: {tool_call['tool']}")
            elif parsed_response.get("ready_for_conclusion"):
                # agent decided it has enough information to conclude
                final_response = self._generate_autonomous_conclusion(state, parsed_response)
                final_state["final_plan"] = final_response
                final_state["budget_status"] = final_response["status"]
                final_state["tool_calls"] = []  # Clear tool calls to signal completion
                print(f"   - Agent Conclusion: {parsed_response.get('reasoning', 'Analysis complete')}")
            
            else:
                # fallback
                final_response_updates = self._generate_final_response(state, "Unable to determine next action")
                final_state.update(final_response_updates)
            
            final_state["current_step"] = current_step + 1
            critical_keys = ['spending_analysis', 'budget_optimization', 'baseline_spending', 'deviation_detected', 'deviation_details']
            for key in critical_keys:
                if key in state:
                    if key not in final_state:
                        final_state[key] = state[key]
            return final_state
            
        except Exception as e:
            print(f"   - Agent Error: {e}")
            final_response_updates = self._generate_final_response(state, f"Analysis error: {str(e)}")
            
            # Preserve state and add error response
            final_state = state.copy()
            final_state.update(final_response_updates)
            
            return final_state
    
    def _build_autonomous_system_prompt(self) -> SystemMessage:
        prompt = """You are Tracey, an expert financial analyst agent. Your goal is to conduct a complete financial analysis for the user based on their new transactions.

You must follow this Standard Operating Procedure (SOP) with precision:
1.  **Fetch Data:** Always start by getting the user's transactions using the `get_transactions` tool. Do not proceed without transaction data.
2.  **Process Data:** Once you have transactions, you MUST categorize them using the `categorize_transactions` tool.
3.  **Analyze:** After categorizing, you MUST analyze spending against the budget using the `analyze_spending` tool.
4.  **React to Analysis:** Review the result of `analyze_spending`.
    *   IF `deviation_detected` is `True`, your next step is to call the `optimize_budget` tool to create a reallocation plan.
    *   AFTER a successful optimization, you MUST call the `research_tips` tool to find actionable advice for the categories that are overbudget.
    *   IF `deviation_detected` is `False`, your work is mostly done. You do not need to call `optimize_budget` or `research_tips`.
5.  **Final Report:** Once you have completed all necessary steps according to this SOP and have no more tools to call, you will generate a final, comprehensive summary for the user.

RESPONSE FORMAT:
Respond with JSON containing either:

For tool usage:
{
  "needs_tool": true,
  "reasoning": "Why you need this specific tool",
  "tool_call": {
    "tool": "tool_name",
    "args": {relevant_arguments}
  }
}

For final analysis:
{
  "ready_for_conclusion": true,
  "reasoning": "Analysis complete",
  "status": "alert" if overspending detected, otherwise "good",
  "key_insights": ["Key findings from analysis"],
  "recommendations": ["Actionable recommendations"]
}

Remember: Follow the SOP precisely and use the tools in the correct sequence."""

        return SystemMessage(content=prompt)
    
    def _format_analysis_context(self, state: GraphState) -> List[HumanMessage]:
        # Build MINIMAL context to avoid token limits
        context = {
            "user_profile": state.get("user_context", {}),
            "budget_plan": state.get("budget", {}),
            "data_status": {
                "transactions_count": len(state.get("transactions", [])),
                "is_categorized": bool(state.get("transactions") and 
                                     state["transactions"] and 
                                     "budget_category" in state["transactions"][0]),
                "is_analyzed": state.get("deviation_details") is not None
            },
            "current_step": state.get("current_step", 0)
        }
        
        # Only include SUMMARY of analysis results, not full data
        if state.get("deviation_details"):
            context["spending_summary"] = {
                "deviation_detected": state.get("deviation_detected", False),
                "categories_with_issues": list(state["deviation_details"].keys()),
                "total_categories_analyzed": len(state.get("spending_analysis", {}).get("spending_by_category", {}))
            }
        
        # Show recent tool results SUMMARY only
        if state.get("tool_results"):
            context["recent_tool"] = {
                "last_tool": state["tool_results"][-1].get("tool", "unknown"),
                "results_count": len(state["tool_results"])
            }
        
        analysis_prompt = f"""
CURRENT STATE:
{context}

TASK: Based on this summary, decide your next action for cash flow management.

Remember: Your goal is immediate cash flow rebalancing when overspending occurs.
"""

        return [HumanMessage(content=analysis_prompt)]
    
    def _parse_agent_decision(self, response_content: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                return json.loads(json_text)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            print(f"   - Parse Error: {e}")
            # Smart fallback based on context instead of defaulting to analyze_spending
            lower_response = response_content.lower()
            if "categorize" in lower_response:
                return {
                    "needs_tool": True,
                    "reasoning": "Need to categorize transactions",
                    "tool_call": {"tool": "categorize_transactions", "args": {}}
                }
            elif "optimize" in lower_response or "budget" in lower_response:
                return {
                    "needs_tool": True,
                    "reasoning": "Need to optimize budget",
                    "tool_call": {"tool": "optimize_budget", "args": {}}
                }
            else:
                # Force conclusion to prevent infinite loops
                return {
                    "ready_for_conclusion": True,
                    "reasoning": "Parse error - concluding analysis",
                    "status": "good",
                    "key_insights": [],
                    "recommendations": []
                }
    
    def _generate_autonomous_conclusion(self, state: GraphState, parsed_response: Dict) -> Dict[str, Any]:
        user_context = state.get("user_context", {})
        user_name = user_context.get("name", "User")
        
        # extract insights from agent's analysis
        status = parsed_response.get("status", "good")
        key_insights = parsed_response.get("key_insights", [])
        recommendations = parsed_response.get("recommendations", [])
        
        # 🔧 FIX: Collect BOTH budget optimization AND research recommendations
        budget_recommendations = []
        research_recommendations = []
        
        for result in state.get("tool_results", []):
            if result.get("tool") == "optimize_budget" and "recommendations" in result:
                budget_recommendations.extend(result["recommendations"])
                print(f"  📊 Found {len(result['recommendations'])} budget optimization recommendations")
            elif result.get("tool") == "research_tips" and "recommendations" in result:
                research_recommendations.extend(result["recommendations"])
                print(f"  🔍 Found {len(result['recommendations'])} research recommendations")
                print(f"  🔍 Research recommendations: {result['recommendations'][:2]}")
                print(f"  🔍 Research recommendations: {result['recommendations'][:2]}")
        
        # Combine both types of recommendations
        all_recommendations = budget_recommendations + research_recommendations + recommendations
        
        # build status message
        if status == "alert":
            if state.get("deviation_details"):
                overspent_categories = list(state["deviation_details"].keys())
                message = f"Hi {user_name}, I've identified spending concerns in: {', '.join(overspent_categories)}."
            else:
                message = f"Hi {user_name}, I've identified some financial optimization opportunities."
        else:
            message = f"Hi {user_name}, your finances look healthy! Here's what I observed:"
        
        return {
            "status": status,
            "message": message,
            "recommendations": all_recommendations,
            "budget_recommendations": budget_recommendations,  
            "research_recommendations": research_recommendations, 
            "insights": key_insights,
            "reasoning_history": self.reasoning_history
        }
    
    def _generate_final_response(self, state: GraphState, reason: str = "") -> Dict[str, Any]:
        """Generate final response as a dictionary of changes to merge with state."""
        user_context = state.get("user_context", {})
        user_name = user_context.get("name", "User")
        
        # determine status based on available data
        if state.get("deviation_detected"):
            status = "alert"
            message = f"Hi {user_name}, I've completed my analysis and found some areas for improvement."
        else:
            status = "good"
            message = f"Hi {user_name}, your spending appears to be on track."
        
        if reason:
            message += f" ({reason})"
        
        # collect budget optimization and research recommendations
        budget_recommendations = []
        research_recommendations = []
        
        for result in state.get("tool_results", []):
            if result.get("tool") == "optimize_budget" and "recommendations" in result:
                budget_recommendations.extend(result["recommendations"])
            elif result.get("tool") == "research_tips" and "recommendations" in result:
                research_recommendations.extend(result["recommendations"])
    
        all_recommendations = budget_recommendations + research_recommendations
        
        final_plan = {
            "status": status,
            "message": message,
            "recommendations": all_recommendations,
            "budget_recommendations": budget_recommendations,  
            "research_recommendations": research_recommendations,  
            "reasoning_history": self.reasoning_history
        }
        
        # return only the changes to be merged with the existing state
        return {
            "final_plan": final_plan,
            "budget_status": status,
            "tool_calls": []  
        }
