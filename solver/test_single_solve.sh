#!/bin/bash

# Test a single GTO solve to verify setup
# This runs just scenario 01 to check everything works

SOLVER_DIR="/root/Documents/Ploit/solver/TexasSolver-v0.2.0-Linux"
CONFIG_FILE="/root/Documents/Ploit/solver/configs/01_SRP_Ks7c3d_cbet.txt"

echo "====================================="
echo "GTO Solver Test - Single Scenario"
echo "Testing: 01_SRP_Ks7c3d_cbet"
echo "Started at: $(date)"
echo "====================================="
echo ""

cd "$SOLVER_DIR"

./console_solver --input_file "$CONFIG_FILE" --resource_dir ./resources --mode holdem

exit_code=$?

echo ""
echo "====================================="
if [ $exit_code -eq 0 ]; then
    echo "✓ Test PASSED"
else
    echo "✗ Test FAILED (exit code: $exit_code)"
fi
echo "Finished at: $(date)"
echo "====================================="
echo ""
echo "Check output file: /root/Documents/Ploit/solver/outputs/01_SRP_Ks7c3d_cbet.json"
