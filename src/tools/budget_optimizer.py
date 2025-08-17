from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import json

class BudgetOptimizer:
    def __init__(self):
        # category relationships and transfer rules
        self.category_relationships = {
            "Housing": {
                "can_receive_from": ["Entertainment", "Food"],
                "transfer_difficulty": "hard",  # housing is usually fixed
                "essential": True
            },
            "Food": {
                "can_receive_from": ["Entertainment", "Healthcare", "Utilities"],
                "can_give_to": ["Housing", "Transportation"],
                "transfer_difficulty": "medium",
                "essential": True
            },
            "Transportation": {
                "can_receive_from": ["Entertainment", "Food"],
                "can_give_to": ["Housing"],
                "transfer_difficulty": "medium",
                "essential": True
            },
            "Utilities": {
                "can_give_to": ["Housing", "Food", "Transportation"],
                "transfer_difficulty": "easy",  
                "essential": True
            },
            "Healthcare": {
                "can_give_to": ["Housing", "Food", "Transportation"],
                "transfer_difficulty": "easy", 
                "essential": True
            },
            "Entertainment": {
                "can_give_to": ["Housing", "Food", "Transportation"],
                "transfer_difficulty": "easy",  # most flexible
                "essential": False
            }
        }
    
    def analyze_and_optimize(self,
                           current_budget: Dict[str, float],
                           total_spending: Dict[str, float], 
                           transactions: List[Dict]) -> Dict:
        
        print(f"\n🔧 BUDGET_OPTIMIZER DEBUG:")
        print(f"  Current budget: {current_budget}")
        print(f"  Total spending received: {total_spending}")
        print(f"  Transactions count: {len(transactions)}")
        
        budget_status = {}
        for category in current_budget.keys():
            spent_amount = total_spending.get(category, 0)  
            budget_amount = current_budget[category]
            overage = spent_amount - budget_amount
            
            budget_status[category] = {
                "budget": budget_amount,
                "spent": spent_amount, 
                "overage": overage,
                "utilization": (spent_amount / budget_amount) * 100 if budget_amount > 0 else 0,
                "new_transactions": 0  
            }
        
        print(f"  Budget status calculated: {budget_status}")
        
        # identify reallocation opportunities
        over_budget_categories = []
        under_utilized_categories = []
        
        for category, status in budget_status.items():
            if status["overage"] > 0:
                over_budget_categories.append((category, status))
            elif status["utilization"] < 60:  # less than 60% utilized
                under_utilized_categories.append((category, status))
        
        print(f"  Over-budget categories: {[cat[0] for cat in over_budget_categories]}")
        print(f"  Under-utilized categories: {[cat[0] for cat in under_utilized_categories]}")
        
        # generate optimization recommendations
        if not over_budget_categories:
            return {
                "optimization_needed": False,
                "message": "All categories are within budget. No optimization needed.",
                "current_status": budget_status
            }
        
        # analyze transaction patterns for each over-budget category
        optimization_plan = self._generate_optimization_plan(
            over_budget_categories,
            under_utilized_categories,
            transactions,
            current_budget
        )
        
        return optimization_plan
    
    def _generate_optimization_plan(self, 
                                  over_budget_categories: List[Tuple], 
                                  under_utilized_categories: List[Tuple],
                                  transactions: List[Dict],
                                  current_budget: Dict[str, float]) -> Dict:
        recommendations = []
        proposed_budget = current_budget.copy()
        total_reallocation = 0
        
        # sort over-budget categories by severity
        over_budget_categories.sort(key=lambda x: x[1]["overage"], reverse=True)
        
        # sort under-utilized categories by available buffer (lowest utilization first)
        under_utilized_categories.sort(key=lambda x: x[1]["utilization"])
        
        for over_category, over_status in over_budget_categories:
            needed_amount = over_status["overage"]
            
            # analyze why this category is over budget
            spending_analysis = self._analyze_category_spending(over_category, transactions)
            
            # find best source categories for reallocation
            reallocation_sources = self._find_reallocation_sources(
                over_category, 
                needed_amount, 
                under_utilized_categories,
                proposed_budget
            )
            
            if reallocation_sources:
                category_recommendations = []
                remaining_need = needed_amount
                
                for source_category, available_amount, transfer_amount in reallocation_sources:
                    if remaining_need <= 0:
                        break
                    
                    actual_transfer = min(transfer_amount, remaining_need)
                    
                    # update proposed budget
                    proposed_budget[source_category] -= actual_transfer
                    proposed_budget[over_category] += actual_transfer
                    
                    # generate reasoning
                    reasoning = self._generate_transfer_reasoning(
                        source_category, 
                        over_category, 
                        actual_transfer,
                        spending_analysis,
                        transactions
                    )
                    
                    category_recommendations.append({
                        "from_category": source_category,
                        "to_category": over_category,
                        "amount": actual_transfer,
                        "reasoning": reasoning
                    })
                    
                    remaining_need -= actual_transfer
                    total_reallocation += actual_transfer
                
                if category_recommendations:
                    recommendations.extend(category_recommendations)
        
        # generate final optimization result
        if recommendations:
            return {
                "optimization_needed": True,
                "total_reallocation": total_reallocation,
                "recommendations": recommendations,
                "proposed_budget": proposed_budget,
                "original_budget": current_budget,
                "summary": self._generate_optimization_summary(recommendations)
            }
        else:
            return {
                "optimization_needed": False,
                "message": "No suitable budget reallocation options found.",
                "recommendations": []
            }
    
    def _analyze_category_spending(self, category: str, transactions: List[Dict]) -> Dict:
        category_transactions = [
            t for t in transactions 
            if t.get('budget_category') == category
        ]
        
        if not category_transactions:
            return {"pattern": "no_data", "description": "No transaction data available"}
        
        # analyze transaction patterns
        total_amount = sum(t.get('amount', 0) for t in category_transactions)
        avg_transaction = total_amount / len(category_transactions)
        
        # find largest transactions
        sorted_transactions = sorted(category_transactions, key=lambda x: x.get('amount', 0), reverse=True)
        largest_transaction = sorted_transactions[0] if sorted_transactions else None
        
        # detect spending patterns
        merchants = [t.get('merchant_name', '') for t in category_transactions]
        recurring_merchants = []
        merchant_counts = {}
        
        for merchant in merchants:
            if merchant:
                merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1
                if merchant_counts[merchant] > 1:
                    recurring_merchants.append(merchant)
        
        # determine pattern type
        if largest_transaction and largest_transaction.get('amount', 0) > avg_transaction * 2:
            pattern = "large_expense"
            description = f"Overage caused by large expense: {largest_transaction.get('description', 'Unknown')} (RM{largest_transaction.get('amount', 0):.0f})"
        elif len(recurring_merchants) > 0:
            pattern = "recurring_overspend"
            description = f"Regular overspending at: {', '.join(recurring_merchants[:2])}"
        elif len(category_transactions) > 5:
            pattern = "frequent_small"
            description = f"Many small transactions (RM{avg_transaction:.0f} average)"
        else:
            pattern = "general_overspend"
            description = f"General overspending across {len(category_transactions)} transactions"
        
        return {
            "pattern": pattern,
            "description": description,
            "transaction_count": len(category_transactions),
            "average_amount": avg_transaction,
            "largest_transaction": largest_transaction,
            "recurring_merchants": recurring_merchants
        }
    
    def _find_reallocation_sources(self, 
                                 target_category: str, 
                                 needed_amount: float,
                                 under_utilized_categories: List[Tuple],
                                 current_budget: Dict[str, float]) -> List[Tuple]:

        sources = []
        target_relations = self.category_relationships.get(target_category, {})
        can_receive_from = target_relations.get("can_receive_from", [])
        
        for source_category, status in under_utilized_categories:
            # from rulebook check if this source can transfer to target
            source_relations = self.category_relationships.get(source_category, {})
            can_give_to = source_relations.get("can_give_to", [])
            
            if target_category in can_give_to or source_category in can_receive_from:
                # calculate available buffer
                current_utilization = status["utilization"]
                budget_amount = status["budget"]
                
                # only take from categories using < 60%
                if current_utilization < 60:
                    # take up to 20% of their budget, but not more than their unused portion
                    max_transfer = min(
                        budget_amount * 0.2, 
                        budget_amount * (60 - current_utilization) / 100,  
                        needed_amount  
                    )
                    
                    if max_transfer >= 50:  # min RM50 transfer
                        transfer_difficulty = source_relations.get("transfer_difficulty", "medium")
                        priority = self._calculate_transfer_priority(transfer_difficulty, current_utilization)
                        
                        sources.append((source_category, budget_amount * (1 - current_utilization/100), max_transfer))
        
        # sort by transfer difficulty (easier transfers first)
        sources.sort(key=lambda x: self.category_relationships.get(x[0], {}).get("transfer_difficulty", "medium"))
        
        return sources
    
    def _calculate_transfer_priority(self, difficulty: str, utilization: float) -> int:
        difficulty_scores = {"easy": 3, "medium": 2, "hard": 1}
        difficulty_score = difficulty_scores.get(difficulty, 2)
        
        # lower utilization = higher priority for giving
        utilization_score = (100 - utilization) / 100 * 3
        
        return difficulty_score + utilization_score
    
    def _generate_transfer_reasoning(self, 
                                   from_category: str,
                                   to_category: str, 
                                   amount: float,
                                   spending_analysis: Dict,
                                   transactions: List[Dict]) -> str:
        from_relations = self.category_relationships.get(from_category, {})
        to_relations = self.category_relationships.get(to_category, {})
        
        # base reasoning on transfer difficulty and category types
        if from_relations.get("transfer_difficulty") == "easy":
            flexibility_note = f"{from_category} typically has flexible spending that can be adjusted"
        elif from_relations.get("transfer_difficulty") == "medium":
            flexibility_note = f"{from_category} spending can be optimized with some planning"
        else:
            flexibility_note = f"{from_category} requires careful adjustment"
        
        # spending pattern context
        pattern_context = ""
        if spending_analysis.get("pattern") == "large_expense":
            pattern_context = f"The {to_category} overage was caused by a large expense. "
        elif spending_analysis.get("pattern") == "recurring_overspend":
            pattern_context = f"The {to_category} category shows recurring overspending patterns. "
        elif spending_analysis.get("pattern") == "frequent_small":
            pattern_context = f"The {to_category} overage comes from many small transactions. "
        
        reasoning = f"{pattern_context}Reallocating RM{amount:.0f} from {from_category} to {to_category}. {flexibility_note}."
        
        # specific advice based on categories
        if from_category == "Healthcare" and to_category == "Food":
            reasoning += " Consider meal planning to optimize food spending while maintaining health priorities."
        elif from_category == "Entertainment" and to_category == "Housing":
            reasoning += " Reducing entertainment spending to accommodate essential housing costs."
        elif from_category == "Utilities" and to_category in ["Food", "Transportation"]:
            reasoning += " Your utility budget appears over-allocated, allowing for better distribution."
        
        return reasoning
    
    def _generate_optimization_summary(self, recommendations: List[Dict]) -> str:
        total_transfers = len(recommendations)
        total_amount = sum(r["amount"] for r in recommendations)
        
        categories_helped = set(r["to_category"] for r in recommendations)
        categories_optimized = set(r["from_category"] for r in recommendations)
        
        summary = f"Budget optimization plan: {total_transfers} transfers totaling RM{total_amount:.0f}. "
        summary += f"Helping {len(categories_helped)} over-budget categories by optimizing {len(categories_optimized)} under-utilized categories. "
        summary += "This reallocation maintains essential spending while accommodating actual usage patterns."
        
        return summary
