"""
Verification endpoint to prove all statistics are calculated correctly.

This endpoint breaks down every statistic calculation step-by-step,
showing numerators, denominators, and formulas.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any
from backend.database import get_db
from backend.models.database_models import PlayerHandSummary

router = APIRouter(prefix="/api/verify", tags=["Verification"])


@router.get("/{player_name}")
async def verify_player_stats(player_name: str, db: Session = Depends(get_db)):
    """
    Verify all statistics are calculated correctly for a player.

    Returns detailed breakdown of every calculation with:
    - Raw counts from boolean flags
    - Formulas used
    - Step-by-step calculations
    - Final percentages
    """

    # Get all hand summaries for this player
    summaries = db.query(PlayerHandSummary).filter(
        PlayerHandSummary.player_name == player_name
    ).all()

    if not summaries:
        raise HTTPException(status_code=404, detail=f"Player '{player_name}' not found")

    total_hands = len(summaries)

    def count_true(attr: str) -> int:
        """Count how many summaries have attribute set to True"""
        return sum(1 for s in summaries if getattr(s, attr, False))

    def calc_pct(numerator: int, denominator: int) -> float:
        """Calculate percentage"""
        if denominator == 0:
            return None
        return round((numerator / denominator) * 100, 2)

    # Build comprehensive verification report
    verification = {
        "player_name": player_name,
        "total_hands": total_hands,
        "statistics": {}
    }

    # ========================================
    # PREFLOP STATISTICS
    # ========================================

    vpip_count = count_true('vpip')
    pfr_count = count_true('pfr')
    limp_count = count_true('limp')

    verification["statistics"]["VPIP%"] = {
        "formula": "(Times put money in pot voluntarily) / (Total hands) × 100",
        "numerator": vpip_count,
        "denominator": total_hands,
        "calculation": f"{vpip_count} / {total_hands} × 100",
        "result": calc_pct(vpip_count, total_hands),
        "interpretation": "Voluntarily Put money In Pot - how often player plays a hand"
    }

    verification["statistics"]["PFR%"] = {
        "formula": "(Times raised preflop) / (Total hands) × 100",
        "numerator": pfr_count,
        "denominator": total_hands,
        "calculation": f"{pfr_count} / {total_hands} × 100",
        "result": calc_pct(pfr_count, total_hands),
        "interpretation": "PreFlop Raise - how often player raises preflop"
    }

    verification["statistics"]["VPIP/PFR_Gap"] = {
        "formula": "VPIP% - PFR%",
        "vpip": calc_pct(vpip_count, total_hands),
        "pfr": calc_pct(pfr_count, total_hands),
        "calculation": f"{calc_pct(vpip_count, total_hands)} - {calc_pct(pfr_count, total_hands)}",
        "result": calc_pct(vpip_count, total_hands) - calc_pct(pfr_count, total_hands) if calc_pct(vpip_count, total_hands) and calc_pct(pfr_count, total_hands) else None,
        "interpretation": "Gap between VPIP and PFR - indicates passivity (high gap = calls a lot)"
    }

    # 3-BET STATISTICS
    faced_raise_count = count_true('faced_raise')
    three_bet_opportunity_count = count_true('three_bet_opportunity')
    made_3bet_count = count_true('made_three_bet')
    faced_3bet_count = count_true('faced_three_bet')
    folded_to_3bet_count = count_true('folded_to_three_bet')

    verification["statistics"]["3-Bet%"] = {
        "formula": "(Times made 3-bet) / (Times had 3-bet opportunity) × 100",
        "numerator": made_3bet_count,
        "denominator": three_bet_opportunity_count,
        "calculation": f"{made_3bet_count} / {three_bet_opportunity_count} × 100",
        "result": calc_pct(made_3bet_count, three_bet_opportunity_count),
        "interpretation": "How often player 3-bets when facing an open raise (not counting times when player opened)",
        "note": "Denominator is 'three_bet_opportunity' - only counts when player faced a raise they didn't make"
    }

    verification["statistics"]["Fold_to_3-Bet%"] = {
        "formula": "(Times folded to 3-bet) / (Times faced 3-bet) × 100",
        "numerator": folded_to_3bet_count,
        "denominator": faced_3bet_count,
        "calculation": f"{folded_to_3bet_count} / {faced_3bet_count} × 100",
        "result": calc_pct(folded_to_3bet_count, faced_3bet_count),
        "interpretation": "How often player folds when facing a 3-bet"
    }

    # ========================================
    # CONTINUATION BET STATISTICS
    # ========================================

    cbet_opp_flop = count_true('cbet_opportunity_flop')
    cbet_made_flop = count_true('cbet_made_flop')
    cbet_opp_turn = count_true('cbet_opportunity_turn')
    cbet_made_turn = count_true('cbet_made_turn')
    cbet_opp_river = count_true('cbet_opportunity_river')
    cbet_made_river = count_true('cbet_made_river')

    verification["statistics"]["C-Bet_Flop%"] = {
        "formula": "(Times c-bet flop) / (C-bet opportunities on flop) × 100",
        "numerator": cbet_made_flop,
        "denominator": cbet_opp_flop,
        "calculation": f"{cbet_made_flop} / {cbet_opp_flop} × 100",
        "result": calc_pct(cbet_made_flop, cbet_opp_flop),
        "interpretation": "Continuation bet frequency on flop (as preflop aggressor)"
    }

    verification["statistics"]["C-Bet_Turn%"] = {
        "formula": "(Times c-bet turn) / (C-bet opportunities on turn) × 100",
        "numerator": cbet_made_turn,
        "denominator": cbet_opp_turn,
        "calculation": f"{cbet_made_turn} / {cbet_opp_turn} × 100",
        "result": calc_pct(cbet_made_turn, cbet_opp_turn),
        "interpretation": "Continuation bet frequency on turn"
    }

    verification["statistics"]["C-Bet_River%"] = {
        "formula": "(Times c-bet river) / (C-bet opportunities on river) × 100",
        "numerator": cbet_made_river,
        "denominator": cbet_opp_river,
        "calculation": f"{cbet_made_river} / {cbet_opp_river} × 100",
        "result": calc_pct(cbet_made_river, cbet_opp_river),
        "interpretation": "Continuation bet frequency on river"
    }

    # Facing C-Bets
    faced_cbet_flop = count_true('faced_cbet_flop')
    folded_to_cbet_flop = count_true('folded_to_cbet_flop')
    called_cbet_flop = count_true('called_cbet_flop')
    raised_cbet_flop = count_true('raised_cbet_flop')

    verification["statistics"]["Fold_to_C-Bet_Flop%"] = {
        "formula": "(Times folded to c-bet) / (Times faced c-bet on flop) × 100",
        "numerator": folded_to_cbet_flop,
        "denominator": faced_cbet_flop,
        "calculation": f"{folded_to_cbet_flop} / {faced_cbet_flop} × 100",
        "result": calc_pct(folded_to_cbet_flop, faced_cbet_flop),
        "interpretation": "How often player folds to continuation bet on flop"
    }

    verification["statistics"]["Call_C-Bet_Flop%"] = {
        "formula": "(Times called c-bet) / (Times faced c-bet on flop) × 100",
        "numerator": called_cbet_flop,
        "denominator": faced_cbet_flop,
        "calculation": f"{called_cbet_flop} / {faced_cbet_flop} × 100",
        "result": calc_pct(called_cbet_flop, faced_cbet_flop),
        "interpretation": "How often player calls continuation bet on flop"
    }

    verification["statistics"]["Raise_C-Bet_Flop%"] = {
        "formula": "(Times raised c-bet) / (Times faced c-bet on flop) × 100",
        "numerator": raised_cbet_flop,
        "denominator": faced_cbet_flop,
        "calculation": f"{raised_cbet_flop} / {faced_cbet_flop} × 100",
        "result": calc_pct(raised_cbet_flop, faced_cbet_flop),
        "interpretation": "How often player raises continuation bet on flop"
    }

    # Sanity check
    total_cbet_response = folded_to_cbet_flop + called_cbet_flop + raised_cbet_flop
    verification["statistics"]["C-Bet_Response_Check"] = {
        "note": "Fold% + Call% + Raise% should equal 100% (or close to it)",
        "fold_pct": calc_pct(folded_to_cbet_flop, faced_cbet_flop),
        "call_pct": calc_pct(called_cbet_flop, faced_cbet_flop),
        "raise_pct": calc_pct(raised_cbet_flop, faced_cbet_flop),
        "total": calc_pct(total_cbet_response, faced_cbet_flop),
        "valid": abs(calc_pct(total_cbet_response, faced_cbet_flop) - 100) < 1 if faced_cbet_flop > 0 else None
    }

    # ========================================
    # SHOWDOWN STATISTICS
    # ========================================

    saw_flop_count = count_true('saw_flop')
    went_to_showdown = count_true('went_to_showdown')
    won_at_showdown = count_true('won_at_showdown')

    verification["statistics"]["WTSD%"] = {
        "formula": "(Times went to showdown) / (Times saw flop) × 100",
        "numerator": went_to_showdown,
        "denominator": saw_flop_count,
        "calculation": f"{went_to_showdown} / {saw_flop_count} × 100",
        "result": calc_pct(went_to_showdown, saw_flop_count),
        "interpretation": "Went To ShowDown - how often player goes to showdown when seeing flop"
    }

    verification["statistics"]["W$SD%"] = {
        "formula": "(Times won at showdown) / (Times went to showdown) × 100",
        "numerator": won_at_showdown,
        "denominator": went_to_showdown,
        "calculation": f"{won_at_showdown} / {went_to_showdown} × 100",
        "result": calc_pct(won_at_showdown, went_to_showdown),
        "interpretation": "Won $ at ShowDown - how often player wins when going to showdown"
    }

    # ========================================
    # PLAYER TYPE CLASSIFICATION
    # ========================================

    vpip_pct = calc_pct(vpip_count, total_hands)
    pfr_pct = calc_pct(pfr_count, total_hands)
    gap = vpip_pct - pfr_pct if vpip_pct and pfr_pct else None

    # Determine player type based on logic
    player_type = None
    classification_reason = ""

    if vpip_pct and pfr_pct:
        if vpip_pct > 45 and pfr_pct > 35:
            player_type = "MANIAC"
            classification_reason = f"VPIP {vpip_pct}% > 45 AND PFR {pfr_pct}% > 35"
        elif vpip_pct > 35 and gap > 12:
            player_type = "CALLING_STATION"
            classification_reason = f"VPIP {vpip_pct}% > 35 AND Gap {gap:.2f} > 12"
        elif vpip_pct >= 25 and pfr_pct >= 18 and gap < 12:
            player_type = "LAG"
            classification_reason = f"VPIP {vpip_pct}% >= 25 AND PFR {pfr_pct}% >= 18 AND Gap {gap:.2f} < 12"
        elif 15 <= vpip_pct <= 25 and 12 <= pfr_pct <= 20 and gap < 8:
            player_type = "TAG"
            classification_reason = f"15 <= VPIP {vpip_pct}% <= 25 AND 12 <= PFR {pfr_pct}% <= 20 AND Gap {gap:.2f} < 8"
        elif vpip_pct < 20 and pfr_pct < 15 and gap > 5:
            player_type = "NIT"
            classification_reason = f"VPIP {vpip_pct}% < 20 AND PFR {pfr_pct}% < 15 AND Gap {gap:.2f} > 5"
        elif vpip_pct > 30:
            player_type = "LOOSE_PASSIVE"
            classification_reason = f"VPIP {vpip_pct}% > 30 (fallback category)"
        elif vpip_pct < 25:
            player_type = "TIGHT"
            classification_reason = f"VPIP {vpip_pct}% < 25 (fallback category)"
        else:
            player_type = "UNKNOWN"
            classification_reason = f"No category matched VPIP {vpip_pct}%, PFR {pfr_pct}%, Gap {gap:.2f}"

    verification["player_type_classification"] = {
        "vpip_pct": vpip_pct,
        "pfr_pct": pfr_pct,
        "gap": gap,
        "player_type": player_type,
        "reason": classification_reason,
        "definitions": {
            "NIT": "VPIP < 20%, PFR < 15%, Gap > 5 (tight/passive)",
            "TAG": "15 <= VPIP <= 25%, 12 <= PFR <= 20%, Gap < 8 (tight/aggressive)",
            "LAG": "VPIP >= 25%, PFR >= 18%, Gap < 12 (loose/aggressive)",
            "CALLING_STATION": "VPIP > 35%, Gap > 12 (loose/passive)",
            "MANIAC": "VPIP > 45%, PFR > 35% (very loose/aggressive)",
            "LOOSE_PASSIVE": "VPIP > 30% (fallback)",
            "TIGHT": "VPIP < 25% (fallback)"
        }
    }

    # ========================================
    # SUMMARY
    # ========================================

    verification["summary"] = {
        "total_hands": total_hands,
        "sample_size_quality": "Excellent" if total_hands >= 1000 else "Good" if total_hands >= 500 else "Moderate" if total_hands >= 200 else "Preliminary",
        "key_stats": {
            "VPIP": f"{vpip_pct}%",
            "PFR": f"{pfr_pct}%",
            "3-Bet": f"{calc_pct(made_3bet_count, three_bet_opportunity_count)}%",
            "C-Bet_Flop": f"{calc_pct(cbet_made_flop, cbet_opp_flop)}%",
            "WTSD": f"{calc_pct(went_to_showdown, saw_flop_count)}%",
            "W$SD": f"{calc_pct(won_at_showdown, went_to_showdown)}%"
        },
        "player_type": player_type
    }

    return verification
