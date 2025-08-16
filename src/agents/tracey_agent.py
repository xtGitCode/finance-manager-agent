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
    
    def agent_node(self, state: GraphState) -> GraphState:
        updated_state = state.copy()
        current_step = state.get("current_step", 0)
        
        # safety check to avoid infinity loops, max steps = 10
        if current_step >= 10:
            print("   - Agent: Reached step limit, providing final analysis")
            return self._generate_final_response(state, "Analysis completed after thorough investigation")
        
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
            
            if parsed_response.get("needs_tool"):
                # agent decided it needs more information
                tool_call = parsed_response["tool_call"]
                updated_state["tool_calls"] = [tool_call]
                updated_state["current_analysis"] = parsed_response.get("reasoning", "Gathering additional data")
                print(f"   - Agent Decision: {parsed_response['reasoning']}")
                print(f"   - Tool Selected: {tool_call['tool']}")
                
            elif parsed_response.get("ready_for_conclusion"):
                # agent decided it has enough information to conclude
                final_response = self._generate_autonomous_conclusion(state, parsed_response)
                updated_state["final_plan"] = final_response
                updated_state["budget_status"] = final_response["status"]
                print(f"   - Agent Conclusion: {parsed_response.get('reasoning', 'Analysis complete')}")
            
            else:
                # fallback
                return self._generate_final_response(state, "Unable to determine next action")
            
            updated_state["current_step"] = current_step + 1
            return updated_state
            
        except Exception as e:
            print(f"   - Agent Error: {e}")
            return self._generate_final_response(state, f"Analysis error: {str(e)}")
    
    def _build_autonomous_system_prompt(self) -> SystemMessage:
        prompt = """You are an autonomous Financial Guardian Agent with deep expertise in personal finance analysis, behavioral economics, and data pattern recognition.

MISSION: Independently analyze financial data, recognize spending patterns, and provide intelligent recommendations based on your analysis.

AVAILABLE TOOLS & WHEN TO USE THEM:
- get_transactions: When you need transaction data to begin analysis
- categorize_transactions: When transactions lack proper categorization
- analyze_spending: When you need to compare spending against budget
- research_tips: When you identify specific financial challenges that need solutions
- optimize_budget: When spending patterns suggest budget reallocation would help

AUTONOMOUS REASONING PROCESS:
1. Examine what data is available vs. what you need
2. Identify patterns, anomalies, or concerns in the financial data
3. Determine if you have sufficient information to provide valuable insights
4. Choose tools strategically based on your analysis needs
5. Synthesize findings into actionable, personalized recommendations

KEY PRINCIPLES:
- Think like a financial advisor, not a rule-following system
- Recognize spending patterns organically from the data
- Adapt your analysis approach based on user context
- Research topics should emerge from actual observed patterns
- Provide insights that are specific, actionable, and realistic

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
  "reasoning": "Why you're ready to conclude",
  "status": "good" or "alert",
  "key_insights": ["insight1", "insight2"],
  "recommendations": ["rec1", "rec2"]
}

Think independently. Analyze patterns. Provide value."""

        return SystemMessage(content=prompt)
    
    def _format_analysis_context(self, state: GraphState) -> List[HumanMessage]:
        # build context for agent
        context = {
            "user_profile": state.get("user_context", {}),
            "budget_plan": state.get("budget", {}),
            "available_data": {
                "transactions": len(state.get("transactions", [])),
                "categorized": bool(state.get("transactions") and 
                                 state["transactions"] and 
                                 "budget_category" in state["transactions"][0]),
                "analyzed": state.get("deviation_details") is not None
            },
            "tool_results": state.get("tool_results", []),
            "current_step": state.get("current_step", 0)
        }
        
        # include recent transactions
        if state.get("transactions"):
            context["recent_transactions"] = state["transactions"][:10]
        
        # analysis results
        if state.get("deviation_details"):
            context["spending_analysis"] = state["deviation_details"]
        
        analysis_prompt = f"""
CURRENT FINANCIAL STATE:
{json.dumps(context, indent=2)}

TASK: Analyze this financial data and determine your next action. Look for patterns, identify concerns, and decide whether you need more information or are ready to provide recommendations.

Consider:
- What spending patterns do you observe?
- Are there any financial concerns or opportunities?
- What would be most helpful for this user?
- Do you need additional data or analysis tools?

Provide your autonomous decision based on your expert analysis."""

        return [HumanMessage(content=analysis_prompt)]
    
    def _parse_agent_decision(self, response_content: str) -> Dict[str, Any]:
        # json extraction and handling
        try:
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                return json.loads(json_text)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            print(f"   - Parse Error: {e}")
            if "need" in response_content.lower() and "tool" in response_content.lower():
                return {
                    "needs_tool": True,
                    "reasoning": "Agent indicated tool usage needed",
                    "tool_call": {"tool": "analyze_spending", "args": {}}
                }
            else:
                return {
                    "ready_for_conclusion": True,
                    "reasoning": "Agent ready to conclude",
                    "status": "good"
                }
    
    def _generate_autonomous_conclusion(self, state: GraphState, parsed_response: Dict) -> Dict[str, Any]:
        user_context = state.get("user_context", {})
        user_name = user_context.get("name", "User")
        
        # extract insights from agent's analysis
        status = parsed_response.get("status", "good")
        key_insights = parsed_response.get("key_insights", [])
        recommendations = parsed_response.get("recommendations", [])
        
        # enchance with any research recommendations from tool results
        research_results = [
            result for result in state.get("tool_results", []) 
            if "recommendations" in result and result.get("recommendations")
        ]
        
        if research_results:
            recommendations.extend(research_results[0]["recommendations"])
        
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
            "recommendations": recommendations,
            "insights": key_insights,
            "reasoning_history": self.reasoning_history
        }
    
    def _generate_final_response(self, state: GraphState, reason: str = "") -> GraphState:
        updated_state = state.copy()
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
        
        # include any research recommendations
        recommendations = []
        research_results = [
            result for result in state.get("tool_results", []) 
            if "recommendations" in result and result.get("recommendations")
        ]
        if research_results:
            recommendations = research_results[0]["recommendations"]
        
        final_plan = {
            "status": status,
            "message": message,
            "recommendations": recommendations,
            "reasoning_history": self.reasoning_history
        }
        
        updated_state["final_plan"] = final_plan
        updated_state["budget_status"] = status
        
        return updated_state
