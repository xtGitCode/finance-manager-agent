import requests
from typing import List, Dict, Optional

class ResearchTool:
    def __init__(self, tavily_api_key: Optional[str]):
        self.api_key = tavily_api_key
        self.base_url = "https://api.tavily.com/search"
    
    def search_cost_saving_tips(self, topic: str, category: str, location: str, budget_deficit: float = 0, transaction_details: Dict = None) -> Dict:
        # analyze the overspending pattern and generate smart, actionable recommendations
        smart_recommendations = self._generate_smart_recommendations(topic, category, location, budget_deficit, transaction_details)
        
        # try to get some additional context (but filter it)
        web_recommendations = []
        if self.api_key:
            print(f"✅ Searching for additional {category} savings tips in {location}...")
            try:
                web_recommendations = self._get_filtered_web_recommendations(category, location, budget_deficit)
            except Exception as e:
                print(f"   - Web search failed: {e}")
        
        # combine smart recommendations with filtered web results (limit total to 2)
        all_recommendations = smart_recommendations + web_recommendations[:1]  # Only 1 web result max
        
        return {
            "topic": topic,
            "location": location, 
            "queries_used": [f"smart analysis for {category}", f"local {category} alternatives {location}"],
            "recommendations": all_recommendations[:2],  # Strict limit: max 2 per category
            "raw_results_count": len(all_recommendations)
        }
    
    def _generate_smart_recommendations(self, topic: str, category: str, location: str, deficit: float, transaction_details: Dict = None) -> List[Dict]:
        recommendations = []
        
        if category.lower() == "food":
            if "kfc" in topic.lower() or "fast food" in topic.lower() or "restaurant" in topic.lower():
                recommendations.extend([
                    {
                        "action": "Switch to Local Economy Rice Stalls",
                        "description": f"Replace expensive fast food with local chap fan (economy rice) stalls in {location}. A typical meal costs RM 8-12 vs RM 15-25 at fast food chains. Look for popular stalls during lunch hours for freshest options.",
                        "potential_savings": f"RM {min(deficit * 0.4, 200):.0f}/month",
                        "difficulty": "Easy",
                        "actionable": True
                    },
                    {
                        "action": "Meal Prep Strategy",
                        "description": f"Cook large batches on weekends. Buy ingredients from Tesco or Giant in {location}. Prepare 5-6 meals for RM 30-40 total vs RM 100+ eating out. Focus on rice dishes and curries that keep well.",
                        "potential_savings": f"RM {min(deficit * 0.5, 250):.0f}/month", 
                        "difficulty": "Medium",
                        "actionable": True
                    }
                ])
            elif "grocery" in topic.lower() or "shopping" in topic.lower():
                recommendations.extend([
                    {
                        "action": "Smart Grocery Shopping",
                        "description": f"Shop at wet markets in {location} for fresh produce (50% cheaper than supermarkets). Use grocery apps like HappyFresh for price comparison.",
                        "potential_savings": f"RM {min(deficit * 0.3, 150):.0f}/month",
                        "difficulty": "Easy", 
                        "actionable": True
                    }
                ])
        
        elif category.lower() == "transportation":
            if "uber" in topic.lower() or "grab" in topic.lower():
                recommendations.append({
                    "action": "Use LRT/MRT + Strategic Ride-Sharing", 
                    "description": f"Take LRT to {location} Central, then Grab for final mile only. Monthly LRT pass (RM 100) + occasional Grab vs RM 400+ in daily rides. Use Grab Pool for cheaper shared rides when needed.",
                    "potential_savings": f"RM {min(deficit * 0.6, 300):.0f}/month",
                    "difficulty": "Easy",
                    "actionable": True
                })
        
        elif category.lower() == "entertainment":
            recommendations.append({
                "action": "Free & Low-Cost Entertainment", 
                "description": f"Explore free activities in {location}: public parks, community events, free museum days. Use GroupOn for discounted activities. Replace expensive outings with hiking or home activities.",
                "potential_savings": f"RM {min(deficit * 0.5, 200):.0f}/month",
                "difficulty": "Easy",
                "actionable": True
            })
            
            if "united airlines" in topic.lower() or "airline" in topic.lower() or "flight" in topic.lower():
                recommendations.append({
                    "action": "Switch to Budget Airlines",
                    "description": f"Use Malaysia Airlines, AirAsia, or Firefly for domestic flights instead of premium carriers. Book 2-3 months ahead for 40-60% savings. For KL-Penang, consider KTM ETS train (RM 79 vs RM 300+ flights).",
                    "potential_savings": f"RM {min(deficit * 0.4, 200):.0f}/month",
                    "difficulty": "Easy",
                    "actionable": True
                })
        
        elif category.lower() == "housing":
            # for housing, provide monitoring and analysis advice only (not lifestyle changes)
            if transaction_details and transaction_details.get('transaction_details'):
                # extract actual transaction amounts and descriptions
                transactions = transaction_details['transaction_details']
                large_transactions = [t for t in transactions if t.get('amount', 0) > 500]
                
                if large_transactions:
                    # create specific recommendation based on actual transactions
                    transaction_list = ", ".join([f"{t['description']} (RM{t['amount']:.0f})" for t in large_transactions[:3]])
                    recommendations.append({
                        "action": "Review Large Housing Transactions",
                        "description": f"Your Housing overage of RM{deficit:.0f} includes large payments: {transaction_list}. Review if these are: 1) One-time setup costs that won't recur, 2) Scheduled deposits/investments, or 3) Recurring payments requiring budget adjustment.",
                        "potential_savings": "Varies",
                        "difficulty": "Easy",
                        "actionable": True
                    })
                else:
                    recommendations.append({
                        "action": "Monitor Housing Spending",
                        "description": f"Track your housing expenses to identify any unusual charges or one-time costs. Consider if recent overspending was due to seasonal factors or one-time expenses that won't recur.",
                        "potential_savings": "Varies",
                        "difficulty": "Easy",
                        "actionable": True
                    })
            else:
                recommendations.append({
                    "action": "Monitor Housing Spending",
                    "description": f"Track your housing expenses to identify any unusual charges or one-time costs. Consider if recent overspending was due to seasonal factors or one-time expenses that won't recur.",
                    "potential_savings": "Varies",
                    "difficulty": "Easy",
                    "actionable": True
                })
        
        elif category.lower() in ["housing", "utilities", "healthcare"]:
            recommendations.append({
                "action": f"Monitor {category.title()} Spending",
                "description": f"Track your {category.lower()} expenses to identify any unusual charges or one-time costs. Consider if recent overspending was due to seasonal factors or one-time expenses that won't recur.",
                "potential_savings": "Varies",
                "difficulty": "Easy",
                "actionable": True
            })
        
        # Limit to maximum 2 recommendations per category
        return recommendations[:2]
    
    def _get_filtered_web_recommendations(self, category: str, location: str, deficit: float) -> List[Dict]:
        """Get web recommendations but filter for relevance and actionability"""
        try:
            # Use more specific, local queries
            queries = [
                f"budget {category} tips Malaysia {location}",
                f"save money {category} {location} Malaysia"
            ]
            
            all_results = []
            for query in queries[:1]:  # Limit to 1 web search
                print(f"   - Web search: '{query}'")
                result = self._execute_single_search(query)
                if result and result.get("results"):
                    all_results.extend(result["results"])
            
            # Filter and process results for relevance
            filtered_recommendations = []
            for result in all_results[:2]:  # Limit results
                title = result.get("title", "")
                content = result.get("content", "")
                url = result.get("url", "")
                
                # Filter out irrelevant content
                if self._is_relevant_recommendation(title, content, category):
                    # Clean up the content to be more actionable
                    cleaned_content = self._clean_web_content(content, category, location)
                    if cleaned_content:
                        filtered_recommendations.append({
                            "action": f"Local Tip: {title[:50]}...",
                            "description": cleaned_content,
                            "potential_savings": f"RM {min(deficit * 0.2, 100):.0f}/month",
                            "difficulty": "Varies",
                            "source": url,
                            "actionable": True
                        })
            
            return filtered_recommendations
        except Exception as e:
            print(f"   - Web search error: {e}")
            return []
    
    def _is_relevant_recommendation(self, title: str, content: str, category: str) -> bool:
        irrelevant_keywords = [
            "construction", "building", "developer", "real estate development",
            "infrastructure", "policy", "government", "municipal", "urban planning",
            "affordable housing development", "modular construction", "contractor",
            "apartment hunting", "college students", "rental listings", "property investment"
        ]
        
        text_to_check = (title + " " + content).lower()
        
        # be strict on necessary categories
        if category.lower() in ["housing", "utilities", "healthcare"]:
            necessity_irrelevant = [
                "find apartment", "cheaper rent", "roommate", "move", "relocate",
                "negotiate rent", "mortgage", "refinancing", "housing market"
            ]
            for keyword in necessity_irrelevant:
                if keyword in text_to_check:
                    return False
        
        # check for general irrelevant content
        for keyword in irrelevant_keywords:
            if keyword in text_to_check:
                return False
        
        # for discretionary categories, check for actionable content
        if category.lower() in ["food", "entertainment", "transportation"]:
            actionable_keywords = [
                "tip", "save", "budget", "cheap", "affordable", "discount", 
                "reduce", "cut costs", "alternative", "strategy", "money",
                "local", "meal prep", "public transport", "free activities"
            ]
            return any(keyword in text_to_check for keyword in actionable_keywords)
        
        return False  # default to rejecting web content for necessity categories
    
    def _clean_web_content(self, content: str, category: str, location: str) -> str:
        if len(content) > 300:
            content = content[:300] + "..."
        
        # remove irrelevant phrases
        irrelevant_phrases = [
            "stakeholders from different parts of the system",
            "policy makers", "urban planning", "developers", 
            "construction industry", "real estate market"
        ]
        
        for phrase in irrelevant_phrases:
            content = content.replace(phrase, "")
        
        return content.strip()
    
    def _execute_single_search(self, query: str) -> Dict:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",  # use basic for faster, more focused results
            "max_results": 3
        }
        response = requests.post(self.base_url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
