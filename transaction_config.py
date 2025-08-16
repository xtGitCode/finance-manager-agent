"""
Configuration for Plaid transaction limits and settings
"""

# Transaction limit configurations
TRANSACTION_LIMITS = {
    # Quick analysis (for fast demos)
    "demo": {
        "days_back": 7,
        "limit": 20,
        "description": "Last 20 transactions from past 7 days - for quick demos"
    },
    
    # Standard analysis (recommended)
    "standard": {
        "days_back": 30,
        "limit": 100,
        "description": "Last 100 transactions from past 30 days - balanced analysis"
    },
    
    # Comprehensive analysis
    "comprehensive": {
        "days_back": 90,
        "limit": 500,
        "description": "Last 500 transactions from past 90 days - thorough analysis"
    },
    
    # Light analysis (for testing/development)
    "light": {
        "days_back": 14,
        "limit": 50,
        "description": "Last 50 transactions from past 14 days - light analysis"
    },
    
    # No limits (get everything)
    "unlimited": {
        "days_back": 365,
        "limit": None,
        "description": "All transactions from past year - no limits"
    }
}

# Default configuration
DEFAULT_CONFIG = "standard"

def get_transaction_config(config_name: str = None):
    """
    Get transaction configuration by name
    
    Args:
        config_name: Name of configuration ("demo", "standard", etc.)
                    If None, uses DEFAULT_CONFIG
    
    Returns:
        dict: Configuration with days_back, limit, and description
    """
    if config_name is None:
        config_name = DEFAULT_CONFIG
    
    if config_name not in TRANSACTION_LIMITS:
        print(f"⚠️ Unknown config '{config_name}', using '{DEFAULT_CONFIG}'")
        config_name = DEFAULT_CONFIG
    
    config = TRANSACTION_LIMITS[config_name]
    print(f"📊 Using '{config_name}' config: {config['description']}")
    
    return config

def list_available_configs():
    """List all available transaction limit configurations"""
    print("📋 Available Transaction Limit Configurations:")
    print("=" * 50)
    
    for name, config in TRANSACTION_LIMITS.items():
        days = config['days_back']
        limit = config['limit'] if config['limit'] else "No limit"
        desc = config['description']
        
        print(f"🔸 {name.upper()}")
        print(f"   Days: {days} | Limit: {limit}")
        print(f"   {desc}")
        print()

if __name__ == "__main__":
    # Demo the configuration system
    print("🧪 Testing Transaction Limit Configurations\n")
    
    # List all configs
    list_available_configs()
    
    # Test each config
    for config_name in TRANSACTION_LIMITS.keys():
        config = get_transaction_config(config_name)
        print(f"✅ {config_name}: {config}\n")
