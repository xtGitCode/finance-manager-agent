import os
import time
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter

import plaid
from plaid.api import plaid_api
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.transactions_refresh_request import TransactionsRefreshRequest
from plaid.model.products import Products
from plaid.configuration import Configuration
from plaid.api_client import ApiClient

class PlaidTool:    
    def __init__(self):
        # setup to connect to plaid service
        self.client = None; self._access_token = None
        try:
            plaid_client_id = os.getenv("PLAID_CLIENT_ID"); plaid_secret = os.getenv("PLAID_SECRET")
            if not plaid_client_id or not plaid_secret: raise ValueError("Plaid credentials missing in .env")
            print("✅ Plaid credentials found. Connecting to Sandbox...")
            host = plaid.Environment.Sandbox
            config = Configuration(host=host, api_key={'clientId': plaid_client_id, 'secret': plaid_secret})
            self.client = plaid_api.PlaidApi(ApiClient(config))
            self._initialize_sandbox_item()
        except Exception as e:
            raise ConnectionError(f"Failed to initialize Plaid. Error: {e}")

    def _initialize_sandbox_item(self):
        try:
            # rotate between different sandbox institutions for variety
            institutions = ['ins_109508', 'ins_109509', 'ins_109510', 'ins_109511', 'ins_109512']
            import random
            institution_id = random.choice(institutions)
            print(f"   - Using sandbox institution: {institution_id}")
            
            pt_request = SandboxPublicTokenCreateRequest(institution_id=institution_id, initial_products=[Products('transactions')])
            pt_response = self.client.sandbox_public_token_create(pt_request)
            exchange_response = self.client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=pt_response['public_token']))
            self._access_token = exchange_response['access_token']
            print("✅ Sandbox item created. Triggering transaction refresh...")
            self.client.transactions_refresh(TransactionsRefreshRequest(access_token=self._access_token))
            time.sleep(3)
            print("✅ Transaction refresh complete.")
        except Exception as e:
            raise Exception(f"Could not create sandbox item. Error: {e}")

    def get_transactions(self) -> List[Dict]:
        # receive transactions from plaid sandbox api
        if not self._access_token: return []
        print("   - Fetching transactions from Plaid Sandbox API...")
        try:
            # randomly receive 10-25 transactions
            random_count = random.randint(10, 25)
            request = TransactionsGetRequest(access_token=self._access_token, start_date=(datetime.now() - timedelta(days=30)).date(), end_date=datetime.now().date(), options=TransactionsGetRequestOptions(count=random_count))
            response = self.client.transactions_get(request)
            
            transactions = []
            for t in response['transactions']:
                # randomize amounts for variety
                base_amount = float(t.amount)
                
                # cap extremely large transactions (anything over RM 2000)
                if base_amount > 2000:
                    base_amount = random.uniform(200, 1500)  
                    print(f"   - Capped large transaction to RM {base_amount:.2f}")
                
                # randomly adjust amount by ±10% to create variety
                variance = random.uniform(0.9, 1.1)
                adjusted_amount = base_amount * variance
                
                # add some completely random transactions
                if random.random() < 0.5:  # 20% chance
                    random_merchants = ['Local Coffee Shop', 'Online Purchase', 'Gas Station', 'Grocery Store', 'Restaurant']
                    merchant_name = random.choice(random_merchants)
                    adjusted_amount = random.uniform(10, 200)
                else:
                    merchant_name = t.merchant_name or t.name
                
                transactions.append({
                    'transaction_id': t.transaction_id + f"_{random.randint(1000, 9999)}",  # Make IDs unique
                    'amount': round(adjusted_amount, 2),
                    'date': str(t.date),
                    'description': t.name,
                    'merchant_name': merchant_name,
                    'category': t.category[0] if t.category else 'Other'
                })
            
            print(f"   - Retrieved {len(transactions)} transactions (with caps and randomization)")
            return transactions
        except Exception as e:
            print(f"   - ❌ Plaid API Error: {e}"); return []

    def analyze_spending(self, transactions: List[Dict], budget: Dict, baseline_spending: Dict[str, float] = None) -> Dict:
        print(f"\n🔧 ANALYZE_SPENDING DEBUG:")
        print(f"  Input transactions: {len(transactions)}")
        print(f"  Budget categories: {list(budget.keys())}")
        print(f"  Baseline spending provided: {bool(baseline_spending)}")  # Add this for debugging
        
        if baseline_spending is None:
            baseline_spending = {}
            print(f"  Warning: No baseline spending provided, using empty baseline")
        
        if not transactions:
            print("  ❌ No transactions to analyze!")
            return {
                "analysis_type": "spending_analysis",
                "spending_by_category": baseline_spending.copy(),  # Return baseline if no new transactions
                "deviation_detected": False,
                "deviation_details": {}
            }
        
        # check if transactions have budget_category
        categorized_count = sum(1 for t in transactions if 'budget_category' in t)
        print(f"  Transactions with budget_category: {categorized_count}/{len(transactions)}")
        
        # This part calculates spending from NEW transactions only
        new_spending_by_category = {}
        transaction_debug = []
        
        for txn in transactions:
            # it now relies on the 'budget_category' field added by the new tool
            budget_category = txn.get('budget_category', 'Entertainment') # Fallback
            amount = txn.get('amount', 0)
            
            transaction_debug.append({
                'category': budget_category,
                'amount': amount,
                'description': txn.get('description', '')[:30]
            })
            
            # FIXED: Include ALL transactions (positive AND negative) for accurate net spending
            new_spending_by_category[budget_category] = new_spending_by_category.get(budget_category, 0) + amount
        
        # --- THIS IS THE CRUCIAL NEW LOGIC ---
        # Now, create the TOTAL spending by combining baseline and new spending
        total_spending_by_category = baseline_spending.copy()  # Start with the baseline
        for category, new_spend in new_spending_by_category.items():
            total_spending_by_category[category] = total_spending_by_category.get(category, 0) + new_spend
        # --- END OF NEW LOGIC ---
        
        print(f"  Sample transactions: {len(transaction_debug)} total")
        print(f"  New transaction spending: {new_spending_by_category}")
        print(f"  Baseline spending: {baseline_spending}")
        print(f"  Final TOTAL spending by category: {total_spending_by_category}")
        
        # show negative transactions count only
        negative_count = len([t for t in transaction_debug if t['amount'] < 0])
        if negative_count > 0:
            print(f"  Negative transactions (refunds/credits): {negative_count}")
        
        print(f"  Total spending: RM {sum(total_spending_by_category.values()):.2f}")
        
        deviations, total_overage = {}, 0
        # Use the new total_spending_by_category for deviation check
        for category, spent in total_spending_by_category.items():
            budgeted = budget.get(category, 0)
            if budgeted > 0 and spent > budgeted:
                overage = spent - budgeted
                category_transactions = [t for t in transactions if t.get('budget_category') == category]
                patterns = self._find_spending_patterns(category_transactions)
                is_discretionary = self._analyze_discretionary_spending(category, category_transactions)
                deviations[category] = { 
                    "budgeted": budgeted, 
                    "spent": spent, 
                    "overage": overage, 
                    "is_discretionary": is_discretionary, 
                    "transaction_details": category_transactions, 
                    "patterns": patterns 
                }
                total_overage += overage
        
        # also check for budget categories with no spending
        for budget_category in budget.keys():
            if budget_category not in total_spending_by_category:
                total_spending_by_category[budget_category] = baseline_spending.get(budget_category, 0)
                print(f"  Added missing category {budget_category} with baseline spending: {baseline_spending.get(budget_category, 0)}")
        
        print(f"  Final spending by category (with all budget categories): {total_spending_by_category}")
        print(f"  Deviations found: {list(deviations.keys())}")
        print(f"  Total deviations: {len(deviations)}")
                
        # IMPORTANT: Return the total spending in the result
        return { 
            "analysis_type": "spending_analysis", 
            "spending_by_category": total_spending_by_category,  # This key should now hold the combined spending
            "deviation_detected": bool(deviations), 
            "deviation_details": deviations 
        }

    def _find_spending_patterns(self, transactions: List[Dict]) -> Dict:
        patterns = {}
        merchant_counts = Counter(t['merchant_name'] for t in transactions)
        for merchant, count in merchant_counts.items():
            if count > 1: patterns['recurring_merchant'] = merchant; break
        if transactions:
            highest_txn = max(transactions, key=lambda t: t['amount'])
            if highest_txn['amount'] > 100: patterns['high_value_merchant'] = highest_txn['merchant_name']
        return patterns
    
    def _analyze_discretionary_spending(self, category: str, transactions: List[Dict]) -> bool:
        all_text = ' '.join([t.get('description', '').lower() for t in transactions])
        essential_patterns = { 'Healthcare': ['doctor', 'pharmacy', 'insurance'], 'Housing': ['rent', 'mortgage'], 'Utilities': ['internet', 'phone', 'electric'], 'Food': ['grocery'], 'Transportation': ['gas'] }
        if category in essential_patterns:
            for keyword in essential_patterns[category]:
                if keyword in all_text: return False
        return True