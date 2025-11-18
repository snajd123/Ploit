#!/bin/bash
# Batch solve all 6-max preflop scenarios

SOLVER_DIR="/root/Documents/Ploit/solver/TexasSolver-v0.2.0-Linux"
CONFIG_DIR="/root/Documents/Ploit/solver/preflop_configs"
LOG_DIR="/root/Documents/Ploit/solver/preflop_logs"

mkdir -p "$LOG_DIR"

cd "$SOLVER_DIR"

total=64
completed=0
failed=0

echo "====================================="
echo "6-Max Preflop GTO Batch Solve"
echo "Starting at: $(date)"
echo "====================================="

echo ""
echo "[1/64] Solving: RFI_UTG"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/001_RFI_UTG.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/RFI_UTG.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: RFI_UTG"
    ((completed++))
else
    echo "✗ Failed: RFI_UTG (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[2/64] Solving: RFI_MP"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/002_RFI_MP.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/RFI_MP.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: RFI_MP"
    ((completed++))
else
    echo "✗ Failed: RFI_MP (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[3/64] Solving: RFI_CO"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/003_RFI_CO.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/RFI_CO.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: RFI_CO"
    ((completed++))
else
    echo "✗ Failed: RFI_CO (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[4/64] Solving: RFI_BTN"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/004_RFI_BTN.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/RFI_BTN.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: RFI_BTN"
    ((completed++))
else
    echo "✗ Failed: RFI_BTN (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[5/64] Solving: SB_RFI"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/005_SB_RFI.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/SB_RFI.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: SB_RFI"
    ((completed++))
else
    echo "✗ Failed: SB_RFI (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[6/64] Solving: SB_complete"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/006_SB_complete.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/SB_complete.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: SB_complete"
    ((completed++))
else
    echo "✗ Failed: SB_complete (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[7/64] Solving: BB_vs_SB_limp"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/007_BB_vs_SB_limp.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BB_vs_SB_limp.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BB_vs_SB_limp"
    ((completed++))
else
    echo "✗ Failed: BB_vs_SB_limp (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[8/64] Solving: UTG_open_MP_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/100_UTG_open_MP_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_MP_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_MP_3bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_MP_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[9/64] Solving: UTG_open_CO_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/101_UTG_open_CO_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_CO_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_CO_3bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_CO_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[10/64] Solving: UTG_open_BTN_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/102_UTG_open_BTN_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_BTN_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_BTN_3bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_BTN_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[11/64] Solving: UTG_open_SB_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/103_UTG_open_SB_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_SB_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_SB_3bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_SB_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[12/64] Solving: UTG_open_BB_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/104_UTG_open_BB_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_BB_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_BB_3bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_BB_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[13/64] Solving: MP_open_CO_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/105_MP_open_CO_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_CO_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_CO_3bet"
    ((completed++))
else
    echo "✗ Failed: MP_open_CO_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[14/64] Solving: MP_open_BTN_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/106_MP_open_BTN_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_BTN_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_BTN_3bet"
    ((completed++))
else
    echo "✗ Failed: MP_open_BTN_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[15/64] Solving: MP_open_SB_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/107_MP_open_SB_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_SB_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_SB_3bet"
    ((completed++))
else
    echo "✗ Failed: MP_open_SB_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[16/64] Solving: MP_open_BB_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/108_MP_open_BB_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_BB_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_BB_3bet"
    ((completed++))
else
    echo "✗ Failed: MP_open_BB_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[17/64] Solving: CO_open_BTN_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/109_CO_open_BTN_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_BTN_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_BTN_3bet"
    ((completed++))
else
    echo "✗ Failed: CO_open_BTN_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[18/64] Solving: CO_open_SB_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/110_CO_open_SB_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_SB_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_SB_3bet"
    ((completed++))
else
    echo "✗ Failed: CO_open_SB_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[19/64] Solving: CO_open_BB_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/111_CO_open_BB_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_BB_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_BB_3bet"
    ((completed++))
else
    echo "✗ Failed: CO_open_BB_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[20/64] Solving: BTN_open_SB_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/112_BTN_open_SB_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BTN_open_SB_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BTN_open_SB_3bet"
    ((completed++))
else
    echo "✗ Failed: BTN_open_SB_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[21/64] Solving: BTN_open_BB_3bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/113_BTN_open_BB_3bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BTN_open_BB_3bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BTN_open_BB_3bet"
    ((completed++))
else
    echo "✗ Failed: BTN_open_BB_3bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[22/64] Solving: UTG_open_MP_3bet_UTG_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/200_UTG_open_MP_3bet_UTG_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_MP_3bet_UTG_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_MP_3bet_UTG_4bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_MP_3bet_UTG_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[23/64] Solving: UTG_open_CO_3bet_UTG_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/201_UTG_open_CO_3bet_UTG_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_CO_3bet_UTG_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_CO_3bet_UTG_4bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_CO_3bet_UTG_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[24/64] Solving: UTG_open_BTN_3bet_UTG_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/202_UTG_open_BTN_3bet_UTG_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_BTN_3bet_UTG_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_BTN_3bet_UTG_4bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_BTN_3bet_UTG_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[25/64] Solving: UTG_open_SB_3bet_UTG_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/203_UTG_open_SB_3bet_UTG_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_SB_3bet_UTG_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_SB_3bet_UTG_4bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_SB_3bet_UTG_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[26/64] Solving: UTG_open_BB_3bet_UTG_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/204_UTG_open_BB_3bet_UTG_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_BB_3bet_UTG_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_BB_3bet_UTG_4bet"
    ((completed++))
else
    echo "✗ Failed: UTG_open_BB_3bet_UTG_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[27/64] Solving: MP_open_CO_3bet_MP_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/205_MP_open_CO_3bet_MP_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_CO_3bet_MP_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_CO_3bet_MP_4bet"
    ((completed++))
else
    echo "✗ Failed: MP_open_CO_3bet_MP_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[28/64] Solving: MP_open_BTN_3bet_MP_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/206_MP_open_BTN_3bet_MP_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_BTN_3bet_MP_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_BTN_3bet_MP_4bet"
    ((completed++))
else
    echo "✗ Failed: MP_open_BTN_3bet_MP_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[29/64] Solving: MP_open_SB_3bet_MP_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/207_MP_open_SB_3bet_MP_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_SB_3bet_MP_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_SB_3bet_MP_4bet"
    ((completed++))
else
    echo "✗ Failed: MP_open_SB_3bet_MP_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[30/64] Solving: MP_open_BB_3bet_MP_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/208_MP_open_BB_3bet_MP_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_BB_3bet_MP_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_BB_3bet_MP_4bet"
    ((completed++))
else
    echo "✗ Failed: MP_open_BB_3bet_MP_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[31/64] Solving: CO_open_BTN_3bet_CO_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/209_CO_open_BTN_3bet_CO_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_BTN_3bet_CO_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_BTN_3bet_CO_4bet"
    ((completed++))
else
    echo "✗ Failed: CO_open_BTN_3bet_CO_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[32/64] Solving: CO_open_SB_3bet_CO_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/210_CO_open_SB_3bet_CO_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_SB_3bet_CO_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_SB_3bet_CO_4bet"
    ((completed++))
else
    echo "✗ Failed: CO_open_SB_3bet_CO_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[33/64] Solving: CO_open_BB_3bet_CO_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/211_CO_open_BB_3bet_CO_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_BB_3bet_CO_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_BB_3bet_CO_4bet"
    ((completed++))
else
    echo "✗ Failed: CO_open_BB_3bet_CO_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[34/64] Solving: BTN_open_SB_3bet_BTN_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/212_BTN_open_SB_3bet_BTN_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BTN_open_SB_3bet_BTN_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BTN_open_SB_3bet_BTN_4bet"
    ((completed++))
else
    echo "✗ Failed: BTN_open_SB_3bet_BTN_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[35/64] Solving: BTN_open_BB_3bet_BTN_4bet"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/213_BTN_open_BB_3bet_BTN_4bet.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BTN_open_BB_3bet_BTN_4bet.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BTN_open_BB_3bet_BTN_4bet"
    ((completed++))
else
    echo "✗ Failed: BTN_open_BB_3bet_BTN_4bet (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[36/64] Solving: UTG_open_MP_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/300_UTG_open_MP_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_MP_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_MP_call"
    ((completed++))
else
    echo "✗ Failed: UTG_open_MP_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[37/64] Solving: UTG_open_CO_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/301_UTG_open_CO_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_CO_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_CO_call"
    ((completed++))
else
    echo "✗ Failed: UTG_open_CO_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[38/64] Solving: UTG_open_BTN_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/302_UTG_open_BTN_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_BTN_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_BTN_call"
    ((completed++))
else
    echo "✗ Failed: UTG_open_BTN_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[39/64] Solving: UTG_open_SB_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/303_UTG_open_SB_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_SB_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_SB_call"
    ((completed++))
else
    echo "✗ Failed: UTG_open_SB_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[40/64] Solving: UTG_open_BB_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/304_UTG_open_BB_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_BB_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_BB_call"
    ((completed++))
else
    echo "✗ Failed: UTG_open_BB_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[41/64] Solving: MP_open_CO_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/305_MP_open_CO_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_CO_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_CO_call"
    ((completed++))
else
    echo "✗ Failed: MP_open_CO_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[42/64] Solving: MP_open_BTN_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/306_MP_open_BTN_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_BTN_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_BTN_call"
    ((completed++))
else
    echo "✗ Failed: MP_open_BTN_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[43/64] Solving: MP_open_SB_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/307_MP_open_SB_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_SB_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_SB_call"
    ((completed++))
else
    echo "✗ Failed: MP_open_SB_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[44/64] Solving: MP_open_BB_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/308_MP_open_BB_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_BB_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_BB_call"
    ((completed++))
else
    echo "✗ Failed: MP_open_BB_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[45/64] Solving: CO_open_BTN_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/309_CO_open_BTN_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_BTN_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_BTN_call"
    ((completed++))
else
    echo "✗ Failed: CO_open_BTN_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[46/64] Solving: CO_open_SB_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/310_CO_open_SB_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_SB_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_SB_call"
    ((completed++))
else
    echo "✗ Failed: CO_open_SB_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[47/64] Solving: CO_open_BB_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/311_CO_open_BB_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_BB_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_BB_call"
    ((completed++))
else
    echo "✗ Failed: CO_open_BB_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[48/64] Solving: BTN_open_SB_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/312_BTN_open_SB_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BTN_open_SB_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BTN_open_SB_call"
    ((completed++))
else
    echo "✗ Failed: BTN_open_SB_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[49/64] Solving: BTN_open_BB_call"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/313_BTN_open_BB_call.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BTN_open_BB_call.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BTN_open_BB_call"
    ((completed++))
else
    echo "✗ Failed: BTN_open_BB_call (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[50/64] Solving: UTG_open_MP_call_CO_squeeze"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/400_UTG_open_MP_call_CO_squeeze.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_MP_call_CO_squeeze.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_MP_call_CO_squeeze"
    ((completed++))
else
    echo "✗ Failed: UTG_open_MP_call_CO_squeeze (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[51/64] Solving: UTG_open_MP_call_BTN_squeeze"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/401_UTG_open_MP_call_BTN_squeeze.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_MP_call_BTN_squeeze.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_MP_call_BTN_squeeze"
    ((completed++))
else
    echo "✗ Failed: UTG_open_MP_call_BTN_squeeze (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[52/64] Solving: UTG_open_CO_call_BTN_squeeze"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/402_UTG_open_CO_call_BTN_squeeze.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_CO_call_BTN_squeeze.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_CO_call_BTN_squeeze"
    ((completed++))
else
    echo "✗ Failed: UTG_open_CO_call_BTN_squeeze (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[53/64] Solving: MP_open_CO_call_BTN_squeeze"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/403_MP_open_CO_call_BTN_squeeze.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_CO_call_BTN_squeeze.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_CO_call_BTN_squeeze"
    ((completed++))
else
    echo "✗ Failed: MP_open_CO_call_BTN_squeeze (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[54/64] Solving: CO_open_BTN_call_SB_squeeze"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/404_CO_open_BTN_call_SB_squeeze.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_BTN_call_SB_squeeze.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_BTN_call_SB_squeeze"
    ((completed++))
else
    echo "✗ Failed: CO_open_BTN_call_SB_squeeze (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[55/64] Solving: CO_open_BTN_call_BB_squeeze"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/405_CO_open_BTN_call_BB_squeeze.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_BTN_call_BB_squeeze.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_BTN_call_BB_squeeze"
    ((completed++))
else
    echo "✗ Failed: CO_open_BTN_call_BB_squeeze (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[56/64] Solving: BTN_open_SB_call_BB_squeeze"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/406_BTN_open_SB_call_BB_squeeze.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BTN_open_SB_call_BB_squeeze.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BTN_open_SB_call_BB_squeeze"
    ((completed++))
else
    echo "✗ Failed: BTN_open_SB_call_BB_squeeze (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[57/64] Solving: UTG_open_BB_defend"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/500_UTG_open_BB_defend.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_BB_defend.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_BB_defend"
    ((completed++))
else
    echo "✗ Failed: UTG_open_BB_defend (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[58/64] Solving: UTG_open_SB_defend"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/501_UTG_open_SB_defend.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/UTG_open_SB_defend.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: UTG_open_SB_defend"
    ((completed++))
else
    echo "✗ Failed: UTG_open_SB_defend (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[59/64] Solving: MP_open_BB_defend"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/502_MP_open_BB_defend.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_BB_defend.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_BB_defend"
    ((completed++))
else
    echo "✗ Failed: MP_open_BB_defend (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[60/64] Solving: MP_open_SB_defend"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/503_MP_open_SB_defend.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/MP_open_SB_defend.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: MP_open_SB_defend"
    ((completed++))
else
    echo "✗ Failed: MP_open_SB_defend (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[61/64] Solving: CO_open_BB_defend"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/504_CO_open_BB_defend.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_BB_defend.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_BB_defend"
    ((completed++))
else
    echo "✗ Failed: CO_open_BB_defend (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[62/64] Solving: CO_open_SB_defend"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/505_CO_open_SB_defend.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/CO_open_SB_defend.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: CO_open_SB_defend"
    ((completed++))
else
    echo "✗ Failed: CO_open_SB_defend (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[63/64] Solving: BTN_open_BB_defend"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/506_BTN_open_BB_defend.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BTN_open_BB_defend.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BTN_open_BB_defend"
    ((completed++))
else
    echo "✗ Failed: BTN_open_BB_defend (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "[64/64] Solving: BTN_open_SB_defend"
echo "Started at: $(date)"

./console_solver --input_file "$CONFIG_DIR/507_BTN_open_SB_defend.txt" --resource_dir ./resources --mode holdem \
    > "$LOG_DIR/BTN_open_SB_defend.log" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ Completed: BTN_open_SB_defend"
    ((completed++))
else
    echo "✗ Failed: BTN_open_SB_defend (exit code: $exit_code)"
    ((failed++))
fi
echo "Finished at: $(date)"
echo "---"

echo ""
echo "====================================="
echo "Batch Solve Complete"
echo "Completed: $completed/$total"
echo "Failed: $failed/$total"
echo "Finished at: $(date)"
echo "====================================="