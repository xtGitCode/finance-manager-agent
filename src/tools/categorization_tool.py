from sentence_transformers import SentenceTransformer, util
from typing import Dict, List

class SemanticCategorizer:
    def __init__(self):
        print("🤖 Initializing Semantic Categorizer...")
        # lightweight and fast model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # define our budget categories and descriptive keywords
        self.category_descriptions = {
            "Housing": "rent, mortgage, housing payment",
            "Utilities": "internet, phone bill, electricity, water, gas",
            "Food": "groceries, restaurants, fast food, coffee shop, dining",
            "Transportation": "uber, lyft, public transit, gas station, flights, travel, toll, parking",
            "Healthcare": "doctor visit, pharmacy, hospital, insurance, medical",
            "Entertainment": "movies, concerts, streaming service, netflix, spotify, shopping, clothes, electronics, activities"
        }
        
        self.categories = list(self.category_descriptions.keys())
        
        print("   - Creating semantic signatures for budget categories...")
        self.category_embeddings = self.model.encode(
            [self.category_descriptions[cat] for cat in self.categories],
            convert_to_tensor=True
        )
        print("✅ Semantic Categorizer ready.")

    def categorize_transaction(self, transaction: Dict) -> str:
        description = transaction.get('description', '')
        transaction_embedding = self.model.encode(description, convert_to_tensor=True)
        cosine_scores = util.pytorch_cos_sim(transaction_embedding, self.category_embeddings)
        best_match_index = cosine_scores.argmax()
        
        return self.categories[best_match_index]

    def run(self, transactions: List[Dict]) -> List[Dict]:
        print(f"   - Semantically categorizing {len(transactions)} transactions...")
        for txn in transactions:
            txn['budget_category'] = self.categorize_transaction(txn)
        return transactions