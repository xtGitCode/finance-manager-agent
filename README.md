# Personal Finance Agent - Tracey

Access streamlit demo here: [Financial Guardian - Tracey](https://tracey-finance.streamlit.app/)

An intelligent financial analysis system that demonstrates agentic AI capabilities through autonomous financial monitoring and research-backed decision making. This system serves as a comprehensive investigation into the core components and characteristics of modern AI agents.

## What This System Does

The Financial Guardian is an AI agent named Tracey that acts as your personal financial analyst. Unlike traditional budgeting apps that simply track expenses, Tracey autonomously retrieves your transactions, detects spending patterns, and provides recommendations to optimize your budget allocation.

### Core Components using Agentic AI

**1. Reasoning Engine**
- **Implementation**: TraceyAgent with LangGraph state management
- **Characteristic**: Makes independent decisions through reasoning rather than rule-based workflow
- **Evidence**: Agent dynamically decides which tools to use based on analysis context

**2. Cyclical Decision-Making (ReAct Loop)**
- **Implementation**: Reason → Act → Reason continuous cycle
- **Characteristic**: Agent can reconsider previous decisions with new information
- **Evidence**: After gathering transaction data, agent may decide additional tool calls is needed based on findings

**3. Tool Orchestration & Selection**
- **Implementation**: Dynamic selection from Plaid API, categorization, analysis, optimization, and research tools
- **Characteristic**: Contextual tool usage rather than sequential execution
- **Evidence**: Agent chooses research tools only when budget deviations are detected, not for every analysis

**4. Memory Management**
- **Implementation**: GraphState with simple chronological history
- **Characteristic**: Maintains context across reasoning cycles without information overload
- **Evidence**:  Based on research, "Simple Memory" approach is proven more effective than complex summarization

## How the System Works

### 1. User Setup
When you first access the system, you provide basic information:
- Your name and location (for personalized recommendations)
- Monthly income and work status
- Budget allocations across six main categories

The system uses this information to establish baseline spending expectations and personalize its analysis.

### 2. Autonomous Transaction Analysis
When you click "Update Transactions," Tracey begins its autonomous analysis:

- **Data Retrieval**: Connects to Plaid's sandbox API to fetch simulated transaction data
- **Smart Categorization**: Uses semantic analysis to categorize each transaction into appropriate budget categories
- **Spending Analysis**: Compares actual spending against your budget goals
- **Pattern Recognition**: Identifies spending behaviors and unusual transaction patterns

### 3. Intelligent Deviation Detection
If Tracey finds budget overages, it automatically:
- Calculates the severity of each category's overspending
- Analyzes transaction details to understand spending patterns
- Determines whether expenses are discretionary or essential
- Identifies the root causes of budget deviations

### 4. Dynamic Optimization Engine
When budget issues are detected, Tracey activates its optimization capabilities:
- Finds under-utilized budget categories with available funds
- Proposes specific budget transfers with clear reasoning
- Ensures essential categories are prioritized over discretionary spending
- Provides detailed before-and-after budget comparisons

### 5. Research-Powered Recommendations
For categories with overspending, Tracey conducts targeted research:
- Searches for location-specific money-saving tips
- Generates practical alternatives based on spending patterns
- Provides actionable advice with estimated savings potential
- Focuses on realistic lifestyle adjustments rather than dramatic changes

## Understanding the Interface

### Main Dashboard
- **Budget Status**: Visual indicators for each spending category
- **Update Transactions Button**: Triggers Tracey's complete analysis process
- **Analysis Results**: Comprehensive report after analysis completion

### Agent Logs Panel
- **Live Execution Log**: Real-time view of Tracey's reasoning process
- **Step Tracking**: Sequential display of agent decisions and tool usage
- **Transparency**: Clear indication of what data is being processed and why

### User Profile Sidebar
- **Personal Information**: Basic details for personalized analysis
- **Budget Goals**: Customizable budget allocations across categories
- **Income Tracking**: Monthly income for context and savings calculations

## Technical Implementation

### Architecture
Built using modern AI agent frameworks:
- **LangGraph**: Stateful agent orchestration with cyclical reasoning
- **Groq LLM**: Fast, efficient language model for financial analysis
- **Plaid API**: Secure connection to financial data (sandbox mode)
- **Tavily Research**: Web search capabilities for cost-saving recommendations

### Safety and Privacy
- Uses sandbox financial data only (no real banking connections)
- All analysis happens in real-time without data storage
- Transparent decision-making process visible to users

