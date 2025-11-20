#!/bin/bash
# Run all position-specific GTO solves in parallel
# Generated: 12 position scenarios

cd /root/Documents/Ploit/solver

SOLVER="./console_solver"
CONFIG_DIR="configs_positions"
OUTPUT_DIR="outputs_positions"
LOG_DIR="logs_positions"

# Create directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

echo "======================================"
echo "Position-Specific GTO Solver"
echo "======================================"
echo "Starting: $(date)"
echo "Solver: $SOLVER"
echo "Configs: $CONFIG_DIR"
echo "Outputs: $OUTPUT_DIR"
echo ""

# Function to run a single solve
run_solve() {
    config_file=$1
    base_name=$(basename "$config_file" .txt)
    log_file="$LOG_DIR/${base_name}.log"

    echo "[$(date +%T)] Starting: $base_name"

    # Run solver and capture output
    timeout 600 $SOLVER "$config_file" > "$log_file" 2>&1
    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo "[$(date +%T)] ✓ Completed: $base_name"
    elif [ $exit_code -eq 124 ]; then
        echo "[$(date +%T)] ✗ TIMEOUT: $base_name (>10min)"
    else
        echo "[$(date +%T)] ✗ FAILED: $base_name (exit code: $exit_code)"
    fi
}

# Export function for parallel execution
export -f run_solve
export SOLVER LOG_DIR

# Get all config files
config_files=("$CONFIG_DIR"/*.txt)
total_configs=${#config_files[@]}

echo "Found $total_configs config files"
echo ""

# Run all solves in parallel (max 4 at a time to avoid overload)
printf '%s\n' "${config_files[@]}" | xargs -P 4 -I {} bash -c 'run_solve "$@"' _ {}

echo ""
echo "======================================"
echo "Completed: $(date)"
echo "======================================"
echo ""

# Check results
echo "Results Summary:"
echo "----------------"
success_count=$(ls -1 "$OUTPUT_DIR"/*.json 2>/dev/null | wc -l)
echo "✓ Successful: $success_count / $total_configs"

if [ -d "$OUTPUT_DIR" ]; then
    ls -lh "$OUTPUT_DIR"/*.json 2>/dev/null | awk '{print "  " $9 " - " $5}'
fi

echo ""
echo "Logs available in: $LOG_DIR/"
