#!/bin/bash

# Parallel GTO solver - Run 3 scenarios simultaneously
# System: 8 cores, 15GB RAM
# Per solve: 4 threads, ~900MB RAM
# Parallel: 3 solves = 12 threads (150% CPU), ~2.7GB RAM

CONFIG_DIR="./configs_comprehensive"
LOG_DIR="./logs_comprehensive"
SOLVER="./TexasSolver-v0.2.0-Linux/console_solver"

# Parallel job limit
MAX_PARALLEL=3

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "GTO Parallel Solver - ${MAX_PARALLEL}x Concurrent"
echo "Starting at: $(date)"
echo "========================================="
echo ""

# Count configs
TOTAL=$(ls ${CONFIG_DIR}/*.txt 2>/dev/null | wc -l)
echo "Total scenarios to solve: ${TOTAL}"
echo "Running ${MAX_PARALLEL} solves in parallel"
echo ""

COMPLETED=0
FAILED=0

# Function to solve a scenario
solve_scenario() {
    local config_file="$1"
    local scenario_num="$2"

    filename=$(basename "$config_file" .txt)
    scenario_name="${filename#[0-9][0-9][0-9]_}"

    echo -e "${BLUE}[${scenario_num}/${TOTAL}]${NC} Starting: ${scenario_name}"

    if timeout 30m ${SOLVER} \
        --input_file "${config_file}" \
        --resource_dir ./TexasSolver-v0.2.0-Linux/resources \
        --mode holdem > "${LOG_DIR}/${scenario_name}.log" 2>&1; then

        echo -e "${GREEN}✓ [${scenario_num}/${TOTAL}]${NC} Completed: ${scenario_name}"
        return 0
    else
        echo -e "${RED}✗ [${scenario_num}/${TOTAL}]${NC} Failed: ${scenario_name}"
        return 1
    fi
}

export -f solve_scenario
export SOLVER LOG_DIR TOTAL BLUE GREEN RED NC

# Run with GNU parallel (3 jobs at once)
if command -v parallel &> /dev/null; then
    # Use GNU parallel if available
    echo "Using GNU parallel for optimal scheduling..."
    ls ${CONFIG_DIR}/*.txt | \
        parallel -j ${MAX_PARALLEL} --line-buffer --tagstring '[{#}]' \
        solve_scenario {} {#}
else
    # Fallback: Simple background jobs with xargs
    echo "Using xargs for parallel execution..."
    ls ${CONFIG_DIR}/*.txt | \
        nl | \
        xargs -P ${MAX_PARALLEL} -I {} bash -c '
            read num file <<< "{}"
            solve_scenario "$file" "$num"
        '
fi

# Count results
COMPLETED=$(ls outputs_comprehensive/*.json 2>/dev/null | wc -l)
FAILED=$((TOTAL - COMPLETED))

echo ""
echo "========================================="
echo "Parallel Solving Complete!"
echo "Finished at: $(date)"
echo "========================================="
echo ""
echo "Results:"
echo -e "  ${GREEN}Completed: ${COMPLETED}${NC}"
echo -e "  ${RED}Failed: ${FAILED}${NC}"
echo "  Total: ${TOTAL}"
echo ""
