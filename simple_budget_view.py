import streamlit as st
import streamlit.components.v1 as components

def create_budget_indicator(category, budgeted_amount, total_spent_amount=None, new_transactions_amount=0):
    
    # total_spent_amount should always be provided now from streamlit_app.py
    if total_spent_amount is None:
        # Fallback - should rarely happen
        total_spent_amount = budgeted_amount * 0.5

    # how much over the original budget we are
    overage_amount = total_spent_amount - budgeted_amount
    usage_percentage = 0
    if budgeted_amount > 0:
        usage_percentage = (total_spent_amount / budgeted_amount) * 100

    # conditional colouring
    if usage_percentage <= 50:
        bar_color = "#28a745"  # Green
        status_color = "#28a745"
    elif 50 < usage_percentage <= 100:
        bar_color = "#ffc107"  # Yellow
        status_color = "var(--text-color)"  
    else: # Over budget
        bar_color = "#dc3545"  # Red
        status_color = "#dc3545"

    st.markdown(f"<h5>{category}</h5>", unsafe_allow_html=True)

    metric_col, status_col = st.columns([3, 2])

    with metric_col:
        if usage_percentage > 100:
            spent_display_color = "#dc3545" 
        else:
            spent_display_color = "#ffffff" 

        total_spent_formatted = f'RM{total_spent_amount:,.0f}'
        budgeted_formatted = f'RM{budgeted_amount:,.0f}'

        if new_transactions_amount > 0:
            baseline_amount = total_spent_amount - new_transactions_amount
            baseline_formatted = f'RM{baseline_amount:,.0f}'
            new_txn_formatted = f'RM{new_transactions_amount:,.0f}'
            
            print(f"DEBUG {category}: baseline={baseline_amount}, new={new_transactions_amount}, formatted_new='{new_txn_formatted}'")

            st.markdown(f"**Total: {total_spent_formatted}**", unsafe_allow_html=False)
            st.markdown(f"*Previous: {baseline_formatted} + New: {new_txn_formatted}*", unsafe_allow_html=False)
        else:
            st.markdown(f"**{total_spent_formatted}** / {budgeted_formatted}", unsafe_allow_html=False)

    with status_col:
        if new_transactions_amount > 0:
            if overage_amount <= 0:
                status_text = "Under Budget"
                amount_display = f'<span style="font-size: 1.1rem; color: #ffffff; font-weight: bold;">RM{abs(overage_amount):,.0f}</span>'
            else:
                status_text = "Over Budget"
                amount_display = f'<span style="font-size: 1.1rem; color: {status_color}; font-weight: bold;">RM{overage_amount:,.0f}</span>'
        else:
            remaining_amount = budgeted_amount - total_spent_amount
            if remaining_amount >= 0:
                status_text = "Remaining"
                amount_display = f'<span style="font-size: 1.1rem; color: #ffffff; font-weight: bold;">RM{remaining_amount:,.0f}</span>'
            else:
                status_text = "Over Budget"
                amount_display = f'<span style="font-size: 1.1rem; color: {status_color}; font-weight: bold;">RM{abs(remaining_amount):,.0f}</span>'

        status_html = f"""
            <div style="text-align: right; margin-top: -10px;">
                <span style="font-size: 0.9rem; color: #6c757d;">{status_text}</span><br>
                {amount_display}
            </div>
        """
        components.html(status_html, height=50)
    progress_visual_width = min(usage_percentage, 100)

    progress_bar_html = f"""
    <div style="background-color: #EAECEE; border-radius: 5px; height: 8px;">
        <div style="background-color: {bar_color}; width: {progress_visual_width}%; border-radius: 5px; height: 100%;">
        </div>
    </div>
    """
    st.markdown(progress_bar_html, unsafe_allow_html=True)