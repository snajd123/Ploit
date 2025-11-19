#!/bin/bash

# Simple parallel solver - 3 jobs at a time using background jobs

CONFIG_DIR="./configs_comprehensive"
LOG_DIR="./logs_comprehensive"
SOLVER="./TexasSolver-v0.2.0-Linux/console_solver"
MAX_JOBS=3

echo "Parallel GTO Solver - ${MAX_JOBS} concurrent jobs"
echo "Started: $(date)"
echo ""

# Function to wait for job slot
wait_for_slot() {
    while [ $(jobs -r | wc -l) -ge $MAX_JOBS ]; do
        sleep 1
    done
}

# Process each config
for config in ${CONFIG_DIR}/*.txt; do
    filename=$(basename "$config" .txt)
    scenario="${filename#[0-9][0-9][0-9]_}"

    wait_for_slot

    echo "[$(date +%H:%M:%S)] Starting: $scenario"

    (
        if timeout 30m ${SOLVER} \
            --input_file "$config" \
            --resource_dir ./TexasSolver-v0.2.0-Linux/resources \
            --mode holdem > "${LOG_DIR}/${scenario}.log" 2>&1; then
            echo "[$(date +%H:%M:%S)] ✓ Completed: $scenario"
        else
            echo "[$(date +%H:%M:%S)] ✗ Failed: $scenario"
        fi
    ) &

    sleep 0.5
done

# Wait for all jobs to complete
wait

echo ""
echo "All solves complete: $(date)"
