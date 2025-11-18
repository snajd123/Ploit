# GTO Wizard Preflop Import Workflow

## Quick Start

### Option 1: Interactive Mode (Easiest)
```bash
cd /root/Documents/Ploit/solver
python3 import_gto_wizard_preflop.py
```

Then for each scenario:
1. Go to GTO Wizard
2. Select the scenario (e.g., "UTG RFI")
3. Copy the range (Ctrl+C)
4. Paste into terminal
5. Optionally add frequencies: `raise=30,call=50,fold=20`

### Option 2: Batch Mode (Faster for many scenarios)
1. Create a file `my_ranges.txt` with format:
   ```
   1|2d2c: 1,2h2c: 1,AhKs: 1,...|raise=100
   4|2d2c: 1,3h3c: 1,...|raise=80,call=15,fold=5
   ```

2. Import:
   ```bash
   python3 import_gto_wizard_preflop.py my_ranges.txt
   ```

## Scenario IDs

### RFI Scenarios (1-7)
- 1: RFI_UTG
- 2: RFI_MP
- 3: RFI_CO
- 4: RFI_BTN (Button raise first in)
- 5: SB_RFI (SB raise vs BB)
- 6: SB_complete (SB limp)
- 7: BB_vs_SB_limp

### 3Bet Scenarios (100-113)
- 100: UTG_open_MP_3bet
- 101: UTG_open_CO_3bet
- 102: UTG_open_BTN_3bet
- 103: UTG_open_SB_3bet
- 104: UTG_open_BB_3bet
- 105: MP_open_CO_3bet
- 106: MP_open_BTN_3bet
- 107: MP_open_SB_3bet
- 108: MP_open_BB_3bet
- 109: CO_open_BTN_3bet
- 110: CO_open_SB_3bet
- 111: CO_open_BB_3bet
- 112: BTN_open_SB_3bet
- 113: BTN_open_BB_3bet

## GTO Wizard Export Format

The format GTO Wizard uses:
```
2d2c: 1,2h2c: 1,2h2d: 1,2s2c: 1,AhKs: 0.5,...
```

Where:
- `2d2c` = specific hand combo (2 of diamonds, 2 of clubs)
- `: 1` = frequency (1 = 100%, 0.5 = 50%)

## Tips

1. **Start with most common scenarios:**
   - RFI_BTN (id=4)
   - BTN_open_BB_3bet (id=113)
   - RFI_CO (id=3)

2. **Action frequencies are optional**
   - If you don't have them, just import the range
   - Can add later

3. **Check import status:**
   ```sql
   psql "$DB_URL" -c "SELECT scenario_name, description FROM gto_solutions WHERE scenario_type='preflop'"
   ```

4. **Time estimate:**
   - Interactive mode: ~30-60 seconds per scenario
   - Batch mode: 5-10 minutes for all 64 scenarios (if prepared)

## Example Interactive Session

```
$ python3 import_gto_wizard_preflop.py

======================================================================
GTO Wizard Preflop Import - Interactive Mode
======================================================================

Scenario: RFI_BTN
Description: BB vs BTN
======================================================================

Paste GTO Wizard range (or 's' to skip, 'q' to quit):
> 2d2c: 1,2h2c: 1,AhKs: 1,...

Enter action frequencies (optional, press Enter to skip):
Format: raise=30,call=50,fold=20
> raise=100

📊 RFI_BTN: 326 combos
✅ RFI_BTN imported successfully
```

## Next Steps

After importing:
1. Test API endpoint: `GET /api/gto/preflop/RFI_BTN`
2. Verify data in database
3. Add more scenarios as needed
