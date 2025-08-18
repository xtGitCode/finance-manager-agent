import subprocess
import sys
import os
from pathlib import Path

def run_tests():
    # project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print("Running Tracey Agent Tests")
    print("=" * 50)
    
    print("\nTest 1: Agentic Behavior Tests")
    print("-" * 30)
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_agent_updated.py",  
            "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        if result.returncode == 0:
            print("✅ Agentic behavior tests PASSED")
        else:
            print("❌ Agentic behavior tests FAILED")
            
    except Exception as e:
        print(f"❌ Error running agentic tests: {e}")
    
    print("\nTest 2: Budget Optimizer Tests")
    print("-" * 30)
    
    budget_test_file = "tests/test_budget_optimizer.py"
    if os.path.exists(budget_test_file):
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                budget_test_file,
                "-v", "--tb=short"
            ], capture_output=True, text=True)
            
            print("STDOUT:")
            print(result.stdout)
            
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
                
            if result.returncode == 0:
                print("✅ Budget optimizer tests PASSED")
            else:
                print("❌ Budget optimizer tests FAILED")
                
        except Exception as e:
            print(f"❌ Error running budget optimizer tests: {e}")
    else:
        print("ℹ️  Budget optimizer tests not found - skipping")
    
    # Quick integration test
    print("\n📋 Test 3: Quick Integration Test")
    print("-" * 30)
    
    try:
        # Test that we can import main components
        sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
        
        from main import FinancialGuardianSystem
        from agents.tracey_agent import TraceyAgent
        from agents.graph_state import GraphState
        
        print("✅ Core imports successful")
        
        # Test that agent can be instantiated (with mocked dependencies)
        from unittest.mock import patch
        with patch('agents.tracey_agent.ChatGroq'):
            agent = TraceyAgent("test_key")
            print("✅ Agent instantiation successful")
            
        print("✅ Integration test PASSED")
        
    except Exception as e:
        print(f"❌ Integration test FAILED: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test run complete!")


def run_specific_test(test_name):
    """Run a specific test by name."""
    
    print(f"🧪 Running specific test: {test_name}")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            f"tests/test_agent_updated.py::{test_name}",
            "-v", "-s"  # -s shows print statements
        ], capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        if result.returncode == 0:
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
            
    except Exception as e:
        print(f"❌ Error running {test_name}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        run_specific_test(test_name)
    else:
        # Run all tests
        run_tests()
