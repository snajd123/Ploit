#!/bin/bash

# Run all 15 GTO solver scenarios
# Each solve takes approximately 10-20 minutes
# Total time: 2-5 hours

SOLVER_DIR="/root/Documents/Ploit/solver/TexasSolver-v0.2.0-Linux"
CONFIG_DIR="/root/Documents/Ploit/solver/configs"
LOG_DIR="/root/Documents/Ploit/solver/logs"

mkdir -p "$LOG_DIR"

cd "$SOLVER_DIR"

echo "====================================="
echo "GTO Solver MVP - Batch Run"
echo "Starting at: $(date)"
echo "====================================="
echo ""

# Array of config files
configs=(
    "01_SRP_Ks7c3d_cbet.txt"
    "02_SRP_Ah9s3h_cbet.txt"
    "03_SRP_9s8h7d_cbet.txt"
    "04_SRP_Qc7h2s_cbet.txt"
    "05_SRP_Tc9c5h_cbet.txt"
    "06_SRP_6h5h4s_cbet.txt"
    "07_SRP_AhKd3s_cbet.txt"
    "08_3BET_AhKs9d_cbet.txt"
    "09_SRP_Ts5s5h_cbet.txt"
    "10_SRP_As5d2c_cbet.txt"
    "11_SRP_Kh8h3d_cbet.txt"
    "12_SRP_8d8c3s_cbet.txt"
    "13_SRP_Jh9c8d_cbet.txt"
    "14_SRP_Tc6d2h_cbet.txt"
    "15_SRP_7s5s4s_cbet.txt"
)

# Run each scenario
for i in "${!configs[@]}"; do
    config="${configs[$i]}"
    num=$((i + 1))
    scenario_name="${config%.txt}"

    echo "[$num/15] Solving: $scenario_name"
    echo "Started at: $(date)"

    # Run solver with input file
    ./console_solver --input_file "$CONFIG_DIR/$config" --resource_dir ./resources --mode holdem \
        > "$LOG_DIR/${scenario_name}.log" 2>&1

    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo "✓ Completed: $scenario_name"
    else
        echo "✗ Failed: $scenario_name (exit code: $exit_code)"
    fi

    echo "Finished at: $(date)"
    echo "---"
    echo ""
done

echo "====================================="
echo "All solves completed!"
echo "Finished at: $(date)"
echo "====================================="
echo ""
echo "Output files in: /root/Documents/Ploit/solver/outputs/"
echo "Log files in: $LOG_DIR"
