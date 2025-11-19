#!/bin/bash

# Batch solve all comprehensive scenarios
# Estimated time: ~8-10 hours for 79 scenarios

CONFIG_DIR="./configs_comprehensive"
LOG_DIR="./logs_comprehensive"
SOLVER="./TexasSolver-v0.2.0-Linux/console_solver"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "====================================="
echo "Comprehensive GTO Solver - Batch Run"
echo "Starting at: $(date)"
echo "====================================="
echo ""

# Count total configs
TOTAL=$(ls ${CONFIG_DIR}/*.txt | wc -l)
CURRENT=0
FAILED=0
SUCCESS=0

# Process each config file
for config_file in ${CONFIG_DIR}/*.txt; do
    CURRENT=$((CURRENT + 1))

    # Extract scenario name from filename
    filename=$(basename "$config_file" .txt)
    scenario_name="${filename#[0-9][0-9][0-9]_}"  # Remove number prefix

    echo -e "${BLUE}[${CURRENT}/${TOTAL}]${NC} Solving: ${scenario_name}"
    echo "Started at: $(date)"

    # Run solver
    if timeout 30m ${SOLVER} --input_file "${config_file}" \
        --resource_dir ./TexasSolver-v0.2.0-Linux/resources \
        --mode holdem > "${LOG_DIR}/${scenario_name}.log" 2>&1; then

        echo -e "${GREEN}✓${NC} Completed: ${scenario_name}"
        SUCCESS=$((SUCCESS + 1))
    else
        EXIT_CODE=$?
        echo -e "${RED}✗${NC} Failed: ${scenario_name} (exit code: ${EXIT_CODE})"
        FAILED=$((FAILED + 1))
    fi

    echo "Finished at: $(date)"
    echo "---"
    echo ""
done

echo ""
echo "====================================="
echo "Batch Run Complete!"
echo "Finished at: $(date)"
echo "====================================="
echo ""
echo "Results:"
echo "  Total scenarios: ${TOTAL}"
echo -e "  ${GREEN}Successful: ${SUCCESS}${NC}"
echo -e "  ${RED}Failed: ${FAILED}${NC}"
echo ""
echo "Next steps:"
echo "  1. Parse solutions: python3 ../backend/scripts/parse_gto_solutions.py"
echo "  2. Import to database: python3 ../backend/scripts/run_gto_migration.py"
echo ""
