import streamlit as st
import sys
import os
import time
from datetime import datetime
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.main import FinancialGuardianSystem
from simple_budget_view import create_budget_indicator
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Tracey Financial Agent", page_icon="💲", layout="wide", initial_sidebar_state="expanded")

def main():
    if 'analysis_complete' not in st.session_state: st.session_state.analysis_complete = False
    if 'guardian_result' not in st.session_state: st.session_state.guardian_result = None
    if 'execution_log' not in st.session_state: st.session_state.execution_log = []
    if 'guardian_system' not in st.session_state:
        with st.spinner("Initializing Agent System..."):
            st.session_state.guardian_system = FinancialGuardianSystem()
    if 'original_budget' not in st.session_state: st.session_state.original_budget = None
    if 'current_budget' not in st.session_state: st.session_state.current_budget = None
    if 'spending_summary' not in st.session_state: st.session_state.spending_summary = None
    if 'baseline_spending' not in st.session_state: st.session_state.baseline_spending = None

    with st.sidebar:
        st.markdown("""
            <style> .sidebar-title { text-align: center; font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-weight: 500; font-size: 38px; margin-bottom: -15px; } </style>
            <p class="sidebar-title">Tracey</p>
            """, unsafe_allow_html=True)
        st.markdown("---")
        
        st.header("User Profile")
        name = st.text_input("Name", value="Xiao Thung", help="Your name for personalized analysis")
        location = st.selectbox("Location", ["Puchong", "Subang", "Kajang", "KL", "Semenyih"], help="Your location for localized recommendations")
        monthly_income = st.number_input("Monthly Income (RM)", value=6000, min_value=1000, step=500, help="Your monthly gross income")
        work_status = st.selectbox("Work Status", ["employed", "self-employed", "student", "retired"], help="Your current employment status")
        user_context = {"name": name, "location": location, "monthly_income": str(monthly_income), "work_status": work_status}
        
        st.markdown("---")
        st.header("Budget Goals")
        
        default_housing = int(monthly_income * 0.30); default_food = int(monthly_income * 0.20); default_transport = int(monthly_income * 0.15)
        default_utilities = int(monthly_income * 0.10); default_healthcare = int(monthly_income * 0.05); default_entertainment = int(monthly_income * 0.15)
        
        budget = {
            "Housing": st.number_input("Housing", value=default_housing, min_value=0, step=100),
            "Food": st.number_input("Food", value=default_food, min_value=0, step=50),
            "Transportation": st.number_input("Transportation", value=default_transport, min_value=0, step=50),
            "Utilities": st.number_input("Utilities", value=default_utilities, min_value=0, step=25),
            "Healthcare": st.number_input("Healthcare", value=default_healthcare, min_value=0, step=25),
            "Entertainment": st.number_input("Entertainment", value=default_entertainment, min_value=0, step=25),
        }
        
        total_budget = sum(budget.values())
        st.metric("Total Budget", f"RM {total_budget:,}", f"{(total_budget/monthly_income)*100:.1f}% of income spent")
        
        planned_savings = monthly_income - total_budget
        savings_percentage = (planned_savings / monthly_income) * 100 if monthly_income > 0 else 0
        if planned_savings >= 0: delta_color = "normal"; delta_text = f"{savings_percentage:.1f}% of income"
        else: delta_color = "inverse"; delta_text = "Budget exceeds income!"
        st.metric(label="Planned Savings", value=f"RM {planned_savings:,.0f}", delta=delta_text, delta_color=delta_color)
        
        st.session_state.original_budget = budget.copy()
        if st.session_state.current_budget is None: st.session_state.current_budget = budget.copy()
        
        if st.session_state.baseline_spending is None:
            import random
            st.session_state.baseline_spending = {}
            for category, budget_amount in budget.items():
                baseline_amount = budget_amount * random.uniform(0.1, 0.8)
                st.session_state.baseline_spending[category] = baseline_amount
            print(f"Generated baseline spending: {st.session_state.baseline_spending}")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.header("Dashboard")
        if st.button("Update Transactions", use_container_width=True):
            run_financial_analysis(user_context, budget)
        st.markdown("<hr style='margin-top: 2em; margin-bottom: 1em;'>", unsafe_allow_html=True)
        display_budget_dashboard(st.session_state.current_budget, st.session_state.spending_summary)
        if st.session_state.analysis_complete and st.session_state.guardian_result:
            display_analysis_results(st.session_state.guardian_result)
    with col2:
        st.header("Agent Logs")
        display_agent_log()

def run_financial_analysis(user_context, budget):
    st.session_state.execution_log, st.session_state.analysis_complete, st.session_state.spending_summary = [], False, None
    progress_bar_placeholder, status_text = st.empty(), st.empty()
    baseline_spending = st.session_state.baseline_spending or {}
    print(f"🔍 DEBUG: baseline_spending being passed to agent: {baseline_spending}")
    
    initial_state = { 
        "transactions": [], 
        "budget": budget, 
        "user_context": user_context, 
        "baseline_spending": baseline_spending,  
        "messages": [{"role": "user", "content": "Please analyze my budget for me."}], 
        "current_analysis": None, 
        "deviation_detected": False, 
        "deviation_details": None, 
        "research_queries": [], 
        "tool_calls": [], 
        "tool_results": [], 
        "spending_analysis": None,  
        "budget_optimization": None,  
        "final_plan": None, 
        "budget_status": "unknown", 
        "recovery_recommendations": [], 
        "current_step": 0, 
        "max_steps": 4 
    }
    
    print(f"🔍 INITIAL STATE DEBUG:")
    print(f"  Keys in initial_state: {list(initial_state.keys())}")
    print(f"  baseline_spending in initial_state: {'baseline_spending' in initial_state}")
    print(f"  baseline_spending value: {initial_state.get('baseline_spending', 'NOT FOUND')}")
    
    final_state, step_count, expected_steps = None, 0, 10  
    status_text.info(f"Starting Agent analysis...")
    for output in st.session_state.guardian_system.app.stream(initial_state):
        step_count += 1; node_name = list(output.keys())[0]
        current_state = output[node_name] if node_name != "__end__" else output["__end__"]
        
        progress_bar_placeholder.progress(min(step_count / expected_steps, 0.9))
        
        # enhanced logging with detailed information
        log_entry = create_detailed_log_entry(step_count, node_name, current_state)
        st.session_state.execution_log.append(log_entry)
        
        status_text.info(f"Step {step_count}: {log_entry['description']}")
        if node_name != "__end__": final_state = current_state
        else: final_state = current_state; break
        time.sleep(0.8)
    progress_bar_placeholder.progress(1.0)
    st.session_state.guardian_result = final_state
    st.session_state.analysis_complete = True
    
    # extract spending analysis data
    spending_analysis = final_state.get("spending_analysis")
    if spending_analysis and spending_analysis.get("spending_by_category"):
        st.session_state.spending_summary = spending_analysis["spending_by_category"]
        print(f"🔍 EXTRACTED spending_summary: {st.session_state.spending_summary}")
    
    # extract transactions for display
    if final_state.get("transactions"):
        st.session_state.final_transactions = final_state["transactions"]
        print(f"🔍 EXTRACTED transactions: {len(final_state['transactions'])} items")
    
    # extract budget optimization results
    budget_optimization = final_state.get("budget_optimization")
    if budget_optimization and budget_optimization.get("optimization_needed"):
        proposed_budget = budget_optimization.get("proposed_budget", {})
        if proposed_budget:
            st.session_state.current_budget = proposed_budget
            st.success("📊 Budget optimized based on your spending patterns!")
            print(f"🔍 UPDATED budget: {proposed_budget}")
    
    # show completion status
    final_plan = final_state.get("final_plan", {})
    status = final_plan.get("status", "unknown")
    message = final_plan.get("message", "Analysis complete")
    
    if status == "alert":
        status_text.warning(f"⚠️ {message}")
    elif status == "good":
        status_text.success(f"✅ {message}")
    else:
        status_text.info(f"📊 {message}")
    time.sleep(1); st.rerun()

def create_detailed_log_entry(step_count, node_name, current_state):
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if node_name == "agent":
        # agent reasoning - extract what the agent is thinking about
        tool_calls = current_state.get("tool_calls", [])
        final_plan = current_state.get("final_plan")
        deviation_detected = current_state.get("deviation_detected", False)
        
        if tool_calls:
            # agent decided to call tools
            tool_names = [call.get("tool", "unknown") for call in tool_calls]
            if len(tool_names) == 1:
                tool_name = tool_names[0]
                if tool_name == "get_transactions":
                    description = "Agent decided: Fetch transaction data from Plaid"
                elif tool_name == "categorize_transactions":
                    description = "Agent decided: Categorize transactions into budget categories"
                elif tool_name == "analyze_spending":
                    description = "Agent decided: Analyze spending patterns and detect budget deviations"
                elif tool_name == "optimize_budget":
                    description = "Agent decided: Optimize budget allocation based on spending patterns"
                elif tool_name == "research_tips":
                    args = tool_calls[0].get("args", {})
                    topic = args.get("topic", "general")
                    category = args.get("category", "unknown")
                    description = f"Agent decided: Research savings tips for {category} ({topic})"
                else:
                    description = f"Agent decided: Call {tool_name} tool"
            else:
                description = f"Agent decided: Call {len(tool_names)} tools: {', '.join(tool_names)}"
        elif final_plan:
            # generated final response
            status = final_plan.get("status", "unknown")
            if status == "alert":
                description = "Agent concluded: Budget alert detected, generating recommendations"
            elif status == "good":
                description = "Agent concluded: Budget is on track, no issues found"
            else:
                description = f"Agent concluded: Analysis complete (status: {status})"
        else:
            if deviation_detected:
                description = "Agent reasoning: Analyzing budget deviations and determining next action"
            else:
                description = "Agent reasoning: Processing financial data and assessing budget health"
        
        return {
            "step": step_count,
            "type": "agent",
            "description": description,
            "timestamp": timestamp,
            "details": {
                "tool_calls": tool_calls,
                "deviation_detected": deviation_detected,
                "has_final_plan": bool(final_plan)
            }
        }
    
    elif node_name == "tool_node":
        # show which tools were executed
        tool_results = current_state.get("tool_results", [])
        
        if tool_results:
            latest_result = tool_results[-1]  # get the most recent tool result
            
            if "transactions_retrieved" in latest_result:
                count = latest_result["transactions_retrieved"]
                description = f"Executed: Retrieved {count} transactions from Plaid API"
            elif "transactions_categorized" in latest_result:
                count = latest_result["transactions_categorized"]
                description = f"Executed: Categorized {count} transactions into budget categories"
            elif latest_result.get("analysis_type") == "spending_analysis":
                spending_data = latest_result.get("spending_by_category", {})
                total_spent = sum(spending_data.values())
                categories_with_spending = len([k for k, v in spending_data.items() if v > 0])
                description = f"Executed: Analyzed spending across {categories_with_spending} categories (RM{total_spent:,.0f} total)"
            elif "optimization_needed" in latest_result:
                if latest_result["optimization_needed"]:
                    transfers = len(latest_result.get("recommendations", []))
                    total_reallocation = latest_result.get("total_reallocation", 0)
                    description = f"Executed: Found {transfers} budget optimizations (RM{total_reallocation:.0f} reallocation)"
                else:
                    description = "Executed: No budget optimization opportunities found"
            elif "recommendations" in latest_result:
                rec_count = len(latest_result["recommendations"])
                topic = latest_result.get("topic", "general")
                description = f"Executed: Found {rec_count} savings tips for {topic}"
            else:
                description = "Executed: Tool completed successfully"
        else:
            description = "Executing tools..."
        
        return {
            "step": step_count,
            "type": "tool",
            "description": description,
            "timestamp": timestamp,
            "details": {
                "results_count": len(tool_results),
                "latest_result": latest_result if tool_results else None
            }
        }
    
    else:
        # Completion
        return {
            "step": step_count,
            "type": "complete",
            "description": "Analysis completed successfully",
            "timestamp": timestamp,
            "details": {}
        }

def display_budget_dashboard(current_budget, spending_summary):
    if not current_budget: st.info("Set your budget goals in the sidebar to get started."); return
    st.subheader("Current Budget Status")
    categories = list(current_budget.keys())
    
    if st.session_state.baseline_spending is None:
        import random
        st.session_state.baseline_spending = {}
        for category, budget_amount in current_budget.items():
            baseline_amount = budget_amount * random.uniform(0.2, 0.8)
            st.session_state.baseline_spending[category] = baseline_amount
    
    for i in range(0, len(categories), 2):
        col1, col2 = st.columns(2)
        with col1:
            category1 = categories[i]
            budget_amount1 = current_budget[category1]
            baseline_spending1 = st.session_state.baseline_spending.get(category1, budget_amount1 * 0.5)
            new_transactions1 = spending_summary.get(category1, 0) if spending_summary is not None else 0
            
            # Calculate total spending: spending_summary IS the total (baseline + new transactions)
            if spending_summary is None:
                # Before analysis: show baseline spending vs budget
                create_budget_indicator(category1, budget_amount1, total_spent_amount=baseline_spending1, new_transactions_amount=0)
            else:
                # After analysis: spending_summary contains TOTAL spending, not just new transactions
                total_spent1 = spending_summary.get(category1, baseline_spending1)  # This IS the total from analysis
                new_transactions1 = max(0, total_spent1 - baseline_spending1)       # Calculate new as difference
                create_budget_indicator(category1, budget_amount1, total_spent_amount=total_spent1, new_transactions_amount=new_transactions1)
            
            st.markdown("<div style='margin-bottom: 2em;'></div>", unsafe_allow_html=True)
            
        if i + 1 < len(categories):
            with col2:
                category2 = categories[i + 1]
                budget_amount2 = current_budget[category2]
                baseline_spending2 = st.session_state.baseline_spending.get(category2, budget_amount2 * 0.5)
                new_transactions2 = spending_summary.get(category2, 0) if spending_summary is not None else 0
                
                # Calculate total spending: spending_summary IS the total (baseline + new transactions)
                if spending_summary is None:
                    # Before analysis: show baseline spending vs budget
                    create_budget_indicator(category2, budget_amount2, total_spent_amount=baseline_spending2, new_transactions_amount=0)
                else:
                    # After analysis: spending_summary contains TOTAL spending, not just new transactions
                    total_spent2 = spending_summary.get(category2, baseline_spending2)  # This IS the total from analysis
                    new_transactions2 = max(0, total_spent2 - baseline_spending2)       # Calculate new as difference
                    create_budget_indicator(category2, budget_amount2, total_spent_amount=total_spent2, new_transactions_amount=new_transactions2)
                
                st.markdown("<div style='margin-bottom: 2em;'></div>", unsafe_allow_html=True)

def display_agent_log():
    if st.session_state.execution_log:
        st.subheader("Live Execution Log")
        for log_entry in st.session_state.execution_log:
            step = log_entry['step']
            timestamp = log_entry['timestamp']
            description = log_entry['description']
            log_type = log_entry['type']
            
            if log_type == "agent":
                st.info(f"**Step {step}** ({timestamp})\n{description}")
            elif log_type == "tool":
                st.success(f"**Step {step}** ({timestamp})\n{description}")
            else:  # complete
                st.balloons()
                st.success(f"**Step {step}** ({timestamp})\n{description}")
         
            # Removed the "Show details for Step N" checkbox section
    else: 
        st.info("Click 'Update Transactions' to see the agent in action.")

def display_analysis_results(result):
    if not result: return
    final_plan = result.get("final_plan", {}); status = final_plan.get("status", "unknown"); message = final_plan.get("message", "Analysis complete")
    st.markdown("---"); st.header("Analysis Report")
    
    if status == "error":
        st.error(f"**Analysis Failed:** {message}")
        return # Stop rendering the rest of the report if there was an error
    elif status == "alert":
        st.warning(f"**Budget Alert Detected:** {message}") # Changed to warning for better visual distinction
    else:
        st.success(f"**Budget On Track:** {message}")
    
    # Main change: use budget optimization instead of cash flow rebalancing
    optimization_result = result.get("budget_optimization")
    if optimization_result and optimization_result.get("optimization_needed"):
        display_budget_optimization(optimization_result)
    
    display_transaction_summary(result)
    
    # Display spending charts using the spending_analysis from final state
    spending_analysis = result.get("spending_analysis")
    if spending_analysis and spending_analysis.get("spending_by_category"):
        display_spending_charts(spending_analysis, result.get("budget", {}))
    recommendations = final_plan.get("recommendations", [])
    if recommendations:
        st.subheader("Recommendations by Tracey")
        for i, rec in enumerate(recommendations, 1):
            if isinstance(rec, dict):
                with st.expander(f"Recommendation {i}: {rec.get('action', 'View Details')}"):
                    st.write(f"**Description:** {rec.get('description', 'No description')}")
                    if rec.get('source'): st.write(f"**Source:** [View Source]({rec['source']})")

def display_transaction_summary(result):
    spending_analysis = result.get("spending_analysis")  # Get directly from final state
    all_transactions = result.get("transactions", [])  # Get directly from final state
    
    # Also try to get from session state as backup
    if not all_transactions and hasattr(st.session_state, 'final_transactions'):
        all_transactions = st.session_state.final_transactions
        
    if spending_analysis and all_transactions:
        st.subheader("💳 Transaction Summary")
        total_transactions = len(all_transactions)
        
        # Show summary metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Transactions Analyzed", f"{total_transactions}")
        
        spending_by_category = spending_analysis.get("spending_by_category", {})
        total_spending = sum(spending_by_category.values())
        col2.metric("Total Spending", f"RM {total_spending:,.2f}")
        
        st.markdown("---")
        st.write("**Spending Breakdown by Category**")
        
        for category, total_spent_in_cat in spending_by_category.items():
            budget_amount = result.get("budget", {}).get(category, 0)
            
            # Color code the category based on budget status
            category_title = f"{category} — Spent: RM {total_spent_in_cat:,.2f}"
                
            with st.expander(category_title):
                category_transactions = [t for t in all_transactions if t.get('budget_category') == category]
                if not category_transactions: 
                    st.write("No individual transactions found.")
                    continue
                    
                display_data = [{
                    "Date": t.get('date'), 
                    "Description": t.get('description'), 
                    "Merchant": t.get('merchant_name', 'Unknown'),
                    "Amount": f"RM {t.get('amount', 0):,.2f}"
                } for t in category_transactions]
                
                df = pd.DataFrame(display_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            
    else:
        st.info("No transaction data available. Click 'Update Transactions' to analyze your spending.")

def display_spending_charts(spending_data, budget):
    st.subheader("Spending Analysis")
    
    # Handle both old and new data structure
    if isinstance(spending_data, dict) and "spending_by_category" in spending_data:
        spending_by_category = spending_data["spending_by_category"]
    else:
        spending_by_category = spending_data
    
    categories = list(spending_by_category.keys())
    spending = list(spending_by_category.values())
    budget_amounts = [budget.get(cat, 0) for cat in categories]
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_bar = go.Figure(data=[ 
            go.Bar(name='Budget', x=categories, y=budget_amounts, marker_color='lightblue'), 
            go.Bar(name='Actual Spending', x=categories, y=spending, 
                   marker_color=['#dc3545' if s > b else '#28a745' for s, b in zip(spending, budget_amounts)]) 
        ])
        fig_bar.update_layout(
            title="Budget vs Actual Spending", 
            yaxis_title="Amount (RM)", 
            barmode='group', 
            height=400,
            showlegend=True
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        # Only show positive spending values in pie chart
        positive_spending = [(cat, amt) for cat, amt in zip(categories, spending) if amt > 0]
        if positive_spending:
            pie_categories, pie_values = zip(*positive_spending)
            fig_pie = px.pie(
                values=pie_values, 
                names=pie_categories, 
                title="Spending Distribution", 
                height=400
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No positive spending to display in pie chart.")

def display_budget_optimization(optimization):
    
    st.markdown("---")
    st.header("Smart Budget Optimization")
    
    st.info("**Tracey has detected opportunities to optimize your budget allocation for better financial health!**")
    
    summary = optimization.get("summary", "")
    if summary:
        st.write(summary)
    
    recommendations = optimization.get("recommendations", [])
    if recommendations:
        st.subheader("Budget Adjustments")
        
        total_reallocation = optimization.get("total_reallocation", 0)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.metric("Total Budget Reallocation", f"RM {total_reallocation:.0f}")
        with col2:
            if st.button("Accept Optimization", type="primary"):
                # Apply the proposed budget
                proposed_budget = optimization.get("proposed_budget", {})
                if proposed_budget:
                    st.session_state.current_budget = proposed_budget
                    st.success("Budget optimization applied successfully!")
                    st.rerun()
        
        st.markdown("### Transfer Details")
        
        for i, rec in enumerate(recommendations, 1):
            with st.expander(f"Transfer #{i}: {rec['from_category']} → {rec['to_category']} (RM {rec['amount']:.0f})"):
                st.write(f"**Amount:** RM {rec['amount']:.0f}")
                st.write(f"**From:** {rec['from_category']}")
                st.write(f"**To:** {rec['to_category']}")
                st.write(f"**Reasoning:** {rec['reasoning']}")
                
                # Show impact
                st.markdown("**Impact:**")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"✅ **{rec['to_category']}** gets additional RM {rec['amount']:.0f}")
                with col_b:
                    st.write(f"📉 **{rec['from_category']}** reduces by RM {rec['amount']:.0f}")
        
        # Show before/after budget comparison
        st.markdown("### Budget Comparison")
        
        original_budget = optimization.get("original_budget", {})
        proposed_budget = optimization.get("proposed_budget", {})
        
        comparison_data = []
        for category in original_budget.keys():
            original = original_budget.get(category, 0)
            proposed = proposed_budget.get(category, 0)
            change = proposed - original
            
            comparison_data.append({
                "Category": category,
                "Original Budget": f"RM {original:.0f}",
                "Optimized Budget": f"RM {proposed:.0f}",
                "Change": f"{'+' if change >= 0 else ''}RM {change:.0f}"
            })
        
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("### Why This Optimization Makes Sense")
        
        # Explain the optimization logic
        reasons = []
        for rec in recommendations:
            from_cat = rec['from_category']
            to_cat = rec['to_category']
            
            if from_cat in ["Healthcare", "Utilities"] and to_cat in ["Housing", "Food"]:
                reasons.append(f"• **{from_cat}** typically has buffer room, making it safe to reallocate to essential **{to_cat}** expenses.")
            elif from_cat == "Entertainment" and to_cat in ["Housing", "Food", "Transportation"]:
                reasons.append(f"• **{from_cat}** spending is flexible and can be adjusted to accommodate essential **{to_cat}** needs.")
            elif to_cat == "Housing":
                reasons.append(f"• **Housing** costs are typically fixed, so ensuring adequate budget prevents future financial stress.")
        
        for reason in set(reasons):  # Remove duplicates
            st.write(reason)
        
        st.info("**Tip:** This optimization maintains your essential spending while accommodating your actual usage patterns. You can always adjust manually later.")

if __name__ == "__main__":
    main()