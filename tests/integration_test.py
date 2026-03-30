"""
MATPOWER Web Platform - Integration Tests
Tests the complete end-to-end workflow
"""
import requests
import time
import json
from typing import Dict, Any, List

# API base URL
BASE_URL = "http://localhost:8000"

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}TEST: {name}{Colors.ENDC}")
    print("-" * 60)


def print_success(msg: str):
    print(f"  {Colors.OKGREEN}✓{Colors.ENDC} {msg}")


def print_error(msg: str):
    print(f"  {Colors.FAIL}✗{Colors.ENDC} {msg}")


def print_info(msg: str):
    print(f"  {Colors.OKCYAN}ℹ{Colors.ENDC} {msg}")


def check_backend() -> bool:
    """Check if backend is running"""
    print_test("Backend Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Backend is running (status: {data.get('status')})")
            print_info(f"MATPOWER path: {data.get('matpower_path')}")
            print_info(f"Octave initialized: {data.get('octave_initialized')}")
            return True
        else:
            print_error(f"Backend returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to backend: {e}")
        return False


def test_list_cases() -> List[str]:
    """Test listing available cases"""
    print_test("List Available Cases")
    try:
        response = requests.get(f"{BASE_URL}/api/cases", timeout=10)
        if response.status_code == 200:
            cases = response.json()
            print_success(f"Found {len(cases)} test cases")
            for case in cases[:3]:
                print_info(f"  - {case.get('name')}: {case.get('buses')} buses")
            return [c.get('name') for c in cases]
        else:
            print_error(f"Failed to list cases (status: {response.status_code})")
            return []
    except Exception as e:
        print_error(f"Exception: {e}")
        return []


def test_load_case(case_name: str) -> bool:
    """Test loading a specific case"""
    print_test(f"Load Case: {case_name}")
    try:
        response = requests.get(f"{BASE_URL}/api/cases/{case_name}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Loaded case {case_name}")
            print_info(f"  Base MVA: {data.get('base_mva')}")
            print_info(f"  Buses: {len(data.get('bus', []))}")
            print_info(f"  Generators: {len(data.get('gen', []))}")
            print_info(f"  Branches: {len(data.get('branch', []))}")
            return True
        else:
            print_error(f"Failed to load case (status: {response.status_code})")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_run_power_flow(case_name: str) -> Dict[str, Any]:
    """Test running AC power flow"""
    print_test(f"Run Power Flow: {case_name}")
    try:
        # Use synchronous endpoint
        response = requests.post(
            f"{BASE_URL}/api/simulation/run/sync",
            json={"case_name": case_name, "sim_type": "PF"},
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print_success(f"Power flow converged in {result.get('iterations', 0)} iterations")
                print_info(f"  Execution time: {result.get('et', 0):.3f}s")
                summary = result.get('system_summary', {})
                if summary:
                    print_info(f"  Total generation: {summary.get('total_generation', 0):.2f} MW")
                    print_info(f"  Total load: {summary.get('total_load', 0):.2f} MW")
                    print_info(f"  Total losses: {summary.get('total_losses', 0):.2f} MW")
                    print_info(f"  Voltage range: {summary.get('min_voltage', 0):.3f} - {summary.get('max_voltage', 0):.3f} p.u.")
                return result
            else:
                print_error(f"Power flow failed: {result.get('message', 'Unknown error')}")
                return {}
        else:
            print_error(f"HTTP error: {response.status_code}")
            return {}
    except Exception as e:
        print_error(f"Exception: {e}")
        return {}


def test_run_opf(case_name: str) -> bool:
    """Test running optimal power flow"""
    print_test(f"Run OPF: {case_name}")
    try:
        response = requests.post(
            f"{BASE_URL}/api/simulation/opf",
            params={"case_name": case_name},
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print_success(f"OPF converged in {result.get('iterations', 0)} iterations")
                if result.get('total_cost'):
                    print_info(f"  Total cost: ${result.get('total_cost', 0):.2f}/hr")
                return True
            else:
                print_error(f"OPF failed: {result.get('message', 'Unknown error')}")
                return False
        else:
            print_error(f"HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_disturbance(case_name: str) -> bool:
    """Test applying a disturbance"""
    print_test(f"Apply Disturbance: Line Outage")
    try:
        response = requests.post(
            f"{BASE_URL}/api/simulation/disturbance",
            json={
                "case_name": case_name,
                "disturbance": {
                    "disturbance_type": "line_outage",
                    "target_id": {"f_bus": 1, "t_bus": 2}
                }
            },
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print_success("Disturbance applied and simulation completed")
                return True
            else:
                print_error(f"Simulation failed: {result.get('message')}")
                return False
        else:
            print_error(f"HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_simulation_history() -> bool:
    """Test simulation history"""
    print_test("Simulation History")
    try:
        response = requests.get(f"{BASE_URL}/api/simulation/history", timeout=10)
        if response.status_code == 200:
            history = response.json()
            print_success(f"Found {len(history)} simulation records")
            return True
        else:
            print_error(f"Failed to get history (status: {response.status_code})")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def run_full_test_suite():
    """Run complete integration test suite"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}")
    print("MATPOWER Web Platform - Integration Tests")
    print(f"{'='*60}{Colors.ENDC}\n")

    results = {
        'total': 0,
        'passed': 0,
        'failed': 0
    }

    # Test 1: Backend health
    results['total'] += 1
    if check_backend():
        results['passed'] += 1
    else:
        results['failed'] += 1
        print("\n" + Colors.FAIL + "Backend not running. Exiting tests." + Colors.ENDC)
        return

    # Test 2: List cases
    results['total'] += 1
    case_list = test_list_cases()
    if case_list:
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Use first available case for remaining tests
    if not case_list:
        print("\n" + Colors.FAIL + "No cases available. Exiting tests." + Colors.ENDC)
        return

    test_case = case_list[0]

    # Test 3: Load case
    results['total'] += 1
    if test_load_case(test_case):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 4: Run power flow
    results['total'] += 1
    pf_result = test_run_power_flow(test_case)
    if pf_result:
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 5: Run OPF
    results['total'] += 1
    if test_run_opf(test_case):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 6: Apply disturbance
    results['total'] += 1
    if test_disturbance(test_case):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 7: Simulation history
    results['total'] += 1
    if test_simulation_history():
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Print summary
    print(f"\n{Colors.BOLD}{'='*60}")
    print("Test Summary")
    print(f"{'='*60}{Colors.ENDC}")
    print(f"  Total tests:  {results['total']}")
    print(f"  {Colors.OKGREEN}Passed:{Colors.ENDC}       {results['passed']}")
    print(f"  {Colors.FAIL}Failed:{Colors.ENDC}       {results['failed']}")

    if results['failed'] == 0:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}All tests passed!{Colors.ENDC}\n")
    else:
        print(f"\n{Colors.WARNING}{results['failed']} test(s) failed{Colors.ENDC}\n")


if __name__ == "__main__":
    run_full_test_suite()
