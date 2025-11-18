-- Auto-generated SQL to import GTO solutions
-- Generated from 2 TexasSolver output files


INSERT INTO gto_solutions (
    scenario_name, scenario_type, board,
    position_oop, position_ip,
    pot_size, stack_depth,
    gto_bet_frequency, gto_check_frequency,
    gto_fold_frequency, gto_call_frequency, gto_raise_frequency,
    gto_bet_size_small, gto_bet_size_medium, gto_bet_size_large,
    ev_oop, ev_ip,
    description, solver_version
) VALUES (
    'SRP_Ks7c3d_cbet',
    'srp_flop',
    'Ks7c3d',
    'BB',
    'BTN',
    5.5,
    97.5,
    15.24,
    84.76,
    0.0,
    0.0,
    0.0,
    55,
    109,
    1764,
    NULL,
    NULL,
    'Single raised pot c-bet decision on Ks7c3d board. GTO bets 15.2% of range.',
    'TexasSolver-0.2.0'
)
ON CONFLICT (scenario_name) DO UPDATE SET
    gto_bet_frequency = EXCLUDED.gto_bet_frequency,
    gto_check_frequency = EXCLUDED.gto_check_frequency,
    ev_oop = EXCLUDED.ev_oop,
    ev_ip = EXCLUDED.ev_ip;


INSERT INTO gto_solutions (
    scenario_name, scenario_type, board,
    position_oop, position_ip,
    pot_size, stack_depth,
    gto_bet_frequency, gto_check_frequency,
    gto_fold_frequency, gto_call_frequency, gto_raise_frequency,
    gto_bet_size_small, gto_bet_size_medium, gto_bet_size_large,
    ev_oop, ev_ip,
    description, solver_version
) VALUES (
    '3BET_AhKs9d_cbet',
    '3bet_pot',
    'AhKs9d',
    'BB',
    'BTN',
    20.5,
    90.0,
    4.46,
    95.54,
    0.0,
    0.0,
    0.0,
    39,
    59,
    83,
    NULL,
    NULL,
    '3-bet pot c-bet decision on AhKs9d board. GTO bets 4.5% of range.',
    'TexasSolver-0.2.0'
)
ON CONFLICT (scenario_name) DO UPDATE SET
    gto_bet_frequency = EXCLUDED.gto_bet_frequency,
    gto_check_frequency = EXCLUDED.gto_check_frequency,
    ev_oop = EXCLUDED.ev_oop,
    ev_ip = EXCLUDED.ev_ip;

