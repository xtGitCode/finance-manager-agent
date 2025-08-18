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
    
    def _should_agent_continue(self, state: GraphState) -> bool:
        current_step = state.get("current_step", 0)
        
        # safety limits 
        if current_step >= 10:
            print(f"    ⚠️ Safety limit reached at step {current_step}")
            return False
            
        # Check for tool repetition loops
        recent_tools = [result.get("tool") for result in state.get("tool_results", [])[-4:]]
        tool_counts = {}
        for tool in recent_tools:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        for tool, count in tool_counts.items():
            if count >= 3:  
                print(f"    ⚠️ Tool repetition detected ({tool} run {count} times)")
                return False
        
        return True
    
    def agent_node(self, state: GraphState) -> GraphState:
        current_step = state.get("current_step", 0)
        
        # Check safety limits first
        if not self._should_agent_continue(state):
            final_response_updates = self._generate_final_response(state, "Analysis completed with safety limits")
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
                agent_reasoning = parsed_response.get("reasoning", "Gathering additional data")
                
                final_state["tool_calls"] = [tool_call]
                final_state["current_analysis"] = agent_reasoning
                final_state["agent_reasoning"] = agent_reasoning  # Store for Streamlit
                final_state["agent_decision_type"] = "tool_call"
                
                print(f"   - Agent Decision: {agent_reasoning}")
                print(f"   - Tool Selected: {tool_call['tool']}")
            elif parsed_response.get("ready_for_conclusion"):
                # agent decided it has enough information to conclude
                agent_reasoning = parsed_response.get("reasoning", "Analysis complete")
                
                final_response = self._generate_autonomous_conclusion(state, parsed_response)
                final_state["final_plan"] = final_response
                final_state["budget_status"] = final_response["status"]
                final_state["tool_calls"] = []  # Clear tool calls to signal completion
                final_state["agent_reasoning"] = agent_reasoning  # Store for Streamlit
                final_state["agent_decision_type"] = "conclusion"
                
                print(f"   - Agent Conclusion: {agent_reasoning}")
            
            else:
                # fallback
                fallback_reasoning = "Unable to determine next action"
                final_response_updates = self._generate_final_response(state, fallback_reasoning)
                final_state.update(final_response_updates)
                final_state["agent_reasoning"] = fallback_reasoning
                final_state["agent_decision_type"] = "fallback"
            
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
        prompt = """
        You are Tracey, an expert financial analyst agent. Your goal is to help users understand their financial situation and 
        provide valuable, actionable advice.

        Available tools:
        - get_transactions: Retrieve recent transaction data from financial accounts
        - categorize_transactions: Classify transactions into budget categories for analysis
        - analyze_spending: Compare actual spending against budget and identify issues
        - optimize_budget: Suggest budget reallocations based on spending patterns
        - research_tips: Find relevant money-saving recommendations for specific situations

        Your approach should be thoughtful and adaptive. For each step, consider:
        1. What information do I currently have about this user's financial situation?
        2. What's missing that would help me provide better advice?
        3. What would be most valuable for this specific user right now?
        4. Have I gathered sufficient insights to make meaningful recommendations?

        Reasoning examples:
        - "I need transaction data before I can analyze anything" → get_transactions
        - "I have transactions but they're uncategorized, so I can't identify spending patterns" → categorize_transactions  
        - "I need to understand if there are any budget concerns" → analyze_spending
        - "User is overspending significantly, I should help them rebalance their budget" → optimize_budget
        - "User needs practical advice for their specific overspending areas" → research_tips
        - "I have sufficient information to provide a comprehensive financial assessment" → conclude

        RESPONSE FORMAT:
        Respond with JSON containing either:

        For tool usage:
        {
        "needs_tool": true,
        "reasoning": "Your thought process about why this tool is needed now",
        "tool_call": {
            "tool": "tool_name",
            "args": {relevant_arguments}
        }
        }

        For final analysis:
        {
        "ready_for_conclusion": true,
        "reasoning": "Why you believe you have sufficient information to help the user",
        "status": "alert" if spending concerns detected, otherwise "good",
        "key_insights": ["Key findings from your analysis"],
        "recommendations": ["Actionable advice for the user"]
        }

        Base your decisions on the specific situation, not rigid rules."""

        return SystemMessage(content=prompt)
    
    def _format_analysis_context(self, state: GraphState) -> List[HumanMessage]:
        # Build rich context for reasoning
        user_context = state.get("user_context", {})
        transactions = state.get("transactions", [])
        budget = state.get("budget", {})
        tool_results = state.get("tool_results", [])
        
        # Determine current data status
        has_transactions = len(transactions) > 0
        is_categorized = has_transactions and "budget_category" in transactions[0] if transactions else False
        has_analysis = state.get("spending_analysis") is not None
        deviation_detected = state.get("deviation_detected", False)
        
        # Tools used so far
        tools_used = [result.get("tool") for result in tool_results if result.get("tool")]
        
        context = {
            "user_profile": {
                "name": user_context.get("name", "User"),
                "location": user_context.get("location", "Unknown"),
                "monthly_income": user_context.get("monthly_income", "Unknown")
            },
            "budget_categories": list(budget.keys()),
            "total_budget": sum(budget.values()) if budget else 0,
            "current_data_status": {
                "transactions_available": has_transactions,
                "transaction_count": len(transactions),
                "transactions_categorized": is_categorized,
                "spending_analyzed": has_analysis,
                "issues_detected": deviation_detected
            },
            "tools_used_so_far": tools_used,
            "current_step": state.get("current_step", 0)
        }
        
        # Add analysis insights if available
        if has_analysis and state.get("deviation_details"):
            deviation_details = state["deviation_details"]
            context["analysis_insights"] = {
                "problematic_categories": list(deviation_details.keys()),
                "total_overage": sum(detail.get("overage", 0) for detail in deviation_details.values()),
                "optimization_attempted": "optimize_budget" in tools_used,
                "research_completed": "research_tips" in tools_used
            }
        
        analysis_prompt = f"""
        CURRENT FINANCIAL ANALYSIS SITUATION:
        {json.dumps(context, indent=2)}

        As Tracey, the financial analyst agent, analyze this situation and decide what would be most valuable to do next.

        Consider:
        - What information do I have vs. what do I need?
        - What would help this user most given their current situation?
        - Have I provided sufficient value, or is more analysis needed?

        Decide your next action based on thoughtful reasoning about the user's needs.
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
        budget_recommendations = []
        research_recommendations = []
        
        for result in state.get("tool_results", []):
            if result.get("tool") == "optimize_budget" and "recommendations" in result:
                budget_recommendations.extend(result["recommendations"])
            elif result.get("tool") == "research_tips" and "recommendations" in result:
                research_recommendations.extend(result["recommendations"])
        
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
