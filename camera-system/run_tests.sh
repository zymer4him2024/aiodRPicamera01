#!/bin/bash

# Test runner script for camera detection system
# Runs all tests in sequence and reports results

set -e

echo "=========================================="
echo " Camera Detection System - Test Runner"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo "Activating venv..."
    source venv/bin/activate
fi

echo "Python: $(which python3)"
echo "Python version: $(python3 --version)"
echo ""

# Test results array
declare -a test_results

# Function to run a test
run_test() {
    local test_name="$1"
    local test_script="$2"

    echo "=========================================="
    echo " Running: $test_name"
    echo "=========================================="
    echo ""

    if python3 "$test_script"; then
        echo ""
        echo -e "${GREEN}✅ $test_name: PASSED${NC}"
        test_results+=("PASS:$test_name")
        return 0
    else
        echo ""
        echo -e "${RED}❌ $test_name: FAILED${NC}"
        test_results+=("FAIL:$test_name")
        return 1
    fi
    echo ""
}

# Run tests
echo "Starting test suite..."
echo ""

# Test 1: Camera
if [ "$1" != "--skip-camera" ]; then
    run_test "Camera Test" "test_camera.py" || true
else
    echo "Skipping camera test (--skip-camera flag)"
    test_results+=("SKIP:Camera Test")
fi

echo ""
sleep 2

# Test 2: Hailo Inference
if [ "$1" != "--skip-hailo" ]; then
    run_test "Hailo Inference Test" "test_hailo_inference.py" || true
else
    echo "Skipping Hailo test (--skip-hailo flag)"
    test_results+=("SKIP:Hailo Inference Test")
fi

echo ""
sleep 2

# Test 3: End-to-End (only if previous tests passed)
passed_count=$(printf '%s\n' "${test_results[@]}" | grep -c "PASS:" || true)

if [ "$passed_count" -ge 2 ]; then
    if [ "$1" != "--skip-e2e" ]; then
        run_test "End-to-End Test" "test_end_to_end.py" || true
    else
        echo "Skipping end-to-end test (--skip-e2e flag)"
        test_results+=("SKIP:End-to-End Test")
    fi
else
    echo -e "${YELLOW}⚠️  Skipping end-to-end test due to previous failures${NC}"
    test_results+=("SKIP:End-to-End Test")
fi

# Print summary
echo ""
echo "=========================================="
echo " TEST SUMMARY"
echo "=========================================="
echo ""

total_tests=0
passed_tests=0
failed_tests=0
skipped_tests=0

for result in "${test_results[@]}"; do
    status="${result%%:*}"
    name="${result#*:}"

    total_tests=$((total_tests + 1))

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $name${NC}"
        passed_tests=$((passed_tests + 1))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ $name${NC}"
        failed_tests=$((failed_tests + 1))
    else
        echo -e "${YELLOW}⊘  $name (skipped)${NC}"
        skipped_tests=$((skipped_tests + 1))
    fi
done

echo ""
echo "Total:   $total_tests tests"
echo "Passed:  $passed_tests"
echo "Failed:  $failed_tests"
echo "Skipped: $skipped_tests"
echo ""

if [ $failed_tests -eq 0 ] && [ $passed_tests -gt 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "✅ ALL TESTS PASSED!"
    echo -e "==========================================${NC}"
    echo ""
    echo "Your system is ready for deployment."
    echo ""
    exit 0
else
    echo -e "${RED}=========================================="
    echo "❌ SOME TESTS FAILED"
    echo -e "==========================================${NC}"
    echo ""
    echo "Please check the errors above and:"
    echo "  1. Review HAILO_SETUP_GUIDE.md"
    echo "  2. Check configuration files in config/"
    echo "  3. Verify Hailo device: lsusb | grep Hailo"
    echo "  4. Check logs in logs/ directory"
    echo ""
    exit 1
fi
