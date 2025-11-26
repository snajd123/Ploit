"""
Opponent Frequency Analysis Service

Analyzes opponent tendencies without knowing their hole cards.
Identifies exploitable patterns and recommends adjustments.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import json


class OpponentAnalyzer:
    """
    Analyzes opponent frequencies and identifies exploitable tendencies.
    """

    # GTO baseline frequencies for comparison
    GTO_BASELINES = {
        "vpip": 23.0,  # Typical TAG player
        "pfr": 18.0,
        "three_bet": 5.0,
        "fold_to_three_bet": 60.0,
        "cbet_flop": 65.0,
        "fold_to_cbet_flop": 45.0,
    }

    def __init__(self, db: Session):
        self.db = db

    def analyze_session_opponents(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Analyze all opponents in a session.

        Returns list of opponent analyses with stats, tendencies, and exploits.
        """
        # Get list of opponents (exclude hero)
        opponents = self._get_session_opponents(session_id)

        results = []
        for opponent_name in opponents:
            analysis = self._analyze_opponent(session_id, opponent_name)
            if analysis:
                results.append(analysis)

        # Note: _store_opponent_stats disabled - opponent_session_stats table was dropped
        # if results:
        #     self._store_opponent_stats(results)

        return results

    def _get_session_opponents(self, session_id: int) -> List[str]:
        """
        Get list of opponent names in session (excluding hero with hole cards).
        """
        query = text("""
            SELECT DISTINCT phs.player_name
            FROM player_hand_summary phs
            WHERE phs.session_id = :session_id
            AND phs.hole_cards IS NULL  -- Opponents don't have visible hole cards
            AND (
                SELECT COUNT(*)
                FROM player_hand_summary phs2
                WHERE phs2.session_id = :session_id
                AND phs2.player_name = phs.player_name
            ) >= 20  -- Minimum 20 hands for meaningful stats
            ORDER BY phs.player_name
        """)

        result = self.db.execute(query, {"session_id": session_id})
        return [row[0] for row in result]

    def _analyze_opponent(self, session_id: int, opponent_name: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a single opponent's frequencies and tendencies.
        """
        # Calculate opponent stats
        stats = self._calculate_opponent_stats(session_id, opponent_name)

        if not stats or stats['hands_observed'] < 20:
            return None

        # Compare to GTO and identify tendencies
        tendencies = self._identify_tendencies(stats)

        # Generate exploit recommendations
        exploits = self._generate_exploits(stats, tendencies)

        return {
            "session_id": session_id,
            "opponent_name": opponent_name,
            "hands_observed": stats['hands_observed'],
            **stats,
            "tendencies": tendencies,
            "exploits": exploits
        }

    def _calculate_opponent_stats(self, session_id: int, opponent_name: str) -> Dict[str, Any]:
        """
        Calculate opponent action frequencies.
        """
        query = text("""
            SELECT
                COUNT(*) as hands_observed,

                -- Preflop frequencies
                SUM(CASE WHEN vpip THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as vpip_pct,
                SUM(CASE WHEN pfr THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as pfr_pct,

                -- 3-bet stats (when faced raise)
                SUM(CASE WHEN made_three_bet THEN 1 ELSE 0 END)::float /
                    NULLIF(SUM(CASE WHEN faced_raise THEN 1 ELSE 0 END), 0) * 100 as three_bet_pct,

                -- Fold to 3-bet (when faced 3-bet)
                SUM(CASE WHEN folded_to_three_bet THEN 1 ELSE 0 END)::float /
                    NULLIF(SUM(CASE WHEN faced_three_bet THEN 1 ELSE 0 END), 0) * 100 as fold_to_three_bet_pct,

                -- Postflop stats
                SUM(CASE WHEN saw_flop THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as saw_flop_pct,

                -- Cbet frequency (when has opportunity)
                SUM(CASE WHEN cbet_made_flop THEN 1 ELSE 0 END)::float /
                    NULLIF(SUM(CASE WHEN cbet_opportunity_flop THEN 1 ELSE 0 END), 0) * 100 as cbet_flop_pct,

                -- Fold to cbet (when faced cbet)
                SUM(CASE WHEN folded_to_cbet_flop THEN 1 ELSE 0 END)::float /
                    NULLIF(SUM(CASE WHEN faced_cbet_flop THEN 1 ELSE 0 END), 0) * 100 as fold_to_cbet_flop_pct

            FROM player_hand_summary
            WHERE session_id = :session_id
            AND player_name = :opponent_name
        """)

        result = self.db.execute(query, {
            "session_id": session_id,
            "opponent_name": opponent_name
        })

        row = result.first()
        if not row:
            return {}

        return dict(row._mapping)

    def _identify_tendencies(self, stats: Dict[str, Any]) -> Dict[str, str]:
        """
        Identify opponent tendencies by comparing to GTO baselines.
        """
        tendencies = {}

        # VPIP tendency
        vpip = stats.get('vpip_pct', 0) or 0
        vpip_vs_gto = vpip - self.GTO_BASELINES['vpip']

        if vpip_vs_gto < -10:
            tendencies['preflop'] = "very_tight"
        elif vpip_vs_gto < -5:
            tendencies['preflop'] = "tight"
        elif vpip_vs_gto > 15:
            tendencies['preflop'] = "very_loose"
        elif vpip_vs_gto > 8:
            tendencies['preflop'] = "loose"
        else:
            tendencies['preflop'] = "balanced"

        # Aggression tendency (PFR vs VPIP)
        pfr = stats.get('pfr_pct', 0) or 0
        if vpip > 0:
            aggression_ratio = pfr / vpip
            if aggression_ratio < 0.5:
                tendencies['aggression'] = "passive"
            elif aggression_ratio > 0.8:
                tendencies['aggression'] = "aggressive"
            else:
                tendencies['aggression'] = "balanced"

        # 3-bet tendency
        three_bet = stats.get('three_bet_pct', 0) or 0
        three_bet_vs_gto = three_bet - self.GTO_BASELINES['three_bet']

        if three_bet_vs_gto < -3:
            tendencies['three_bet'] = "rarely_3bets"
        elif three_bet_vs_gto > 5:
            tendencies['three_bet'] = "heavy_3better"
        else:
            tendencies['three_bet'] = "balanced"

        # Fold to cbet tendency
        fold_to_cbet = stats.get('fold_to_cbet_flop_pct', 0) or 0
        fold_to_cbet_vs_gto = fold_to_cbet - self.GTO_BASELINES['fold_to_cbet_flop']

        if fold_to_cbet_vs_gto > 15:
            tendencies['cbet_defense'] = "overfolds"
        elif fold_to_cbet_vs_gto < -15:
            tendencies['cbet_defense'] = "sticky"
        else:
            tendencies['cbet_defense'] = "balanced"

        return tendencies

    def _generate_exploits(self, stats: Dict[str, Any], tendencies: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Generate exploit recommendations based on tendencies.
        """
        exploits = []

        # Exploit tight players - steal more
        if tendencies.get('preflop') in ['tight', 'very_tight']:
            vpip = stats.get('vpip_pct', 0) or 0
            ev_gain = (self.GTO_BASELINES['vpip'] - vpip) * 0.05  # Rough estimate
            exploits.append({
                "exploit_type": "increase_steals",
                "description": f"Opponent is tight ({vpip:.1f}% VPIP). Increase steal frequency in position.",
                "estimated_ev_gain_bb": round(ev_gain, 2),
                "priority": "high" if ev_gain > 1.0 else "medium"
            })

        # Exploit loose players - value bet wider
        if tendencies.get('preflop') in ['loose', 'very_loose']:
            vpip = stats.get('vpip_pct', 0) or 0
            ev_gain = (vpip - self.GTO_BASELINES['vpip']) * 0.04
            exploits.append({
                "exploit_type": "value_bet_wider",
                "description": f"Opponent is loose ({vpip:.1f}% VPIP). Value bet wider ranges, they'll pay you off.",
                "estimated_ev_gain_bb": round(ev_gain, 2),
                "priority": "high" if ev_gain > 1.0 else "medium"
            })

        # Exploit passive players - bluff more
        if tendencies.get('aggression') == 'passive':
            exploits.append({
                "exploit_type": "increase_bluffs",
                "description": "Opponent is passive. Increase bluffing frequency, they won't fight back.",
                "estimated_ev_gain_bb": 0.5,
                "priority": "medium"
            })

        # Exploit players who overfold to cbets
        if tendencies.get('cbet_defense') == 'overfolds':
            fold_to_cbet = stats.get('fold_to_cbet_flop_pct', 0) or 0
            ev_gain = (fold_to_cbet - self.GTO_BASELINES['fold_to_cbet_flop']) * 0.03
            exploits.append({
                "exploit_type": "cbet_more",
                "description": f"Opponent folds too much to cbets ({fold_to_cbet:.1f}%). Cbet with full range.",
                "estimated_ev_gain_bb": round(ev_gain, 2),
                "priority": "high" if ev_gain > 0.8 else "medium"
            })

        # Exploit players who rarely 3-bet
        if tendencies.get('three_bet') == 'rarely_3bets':
            three_bet = stats.get('three_bet_pct', 0) or 0
            exploits.append({
                "exploit_type": "open_wider",
                "description": f"Opponent rarely 3-bets ({three_bet:.1f}%). Open wider ranges, you won't face 3-bets.",
                "estimated_ev_gain_bb": 0.4,
                "priority": "medium"
            })

        return exploits

    def _store_opponent_stats(self, opponent_analyses: List[Dict[str, Any]]):
        """
        Store opponent stats in opponent_session_stats table.
        """
        if not opponent_analyses:
            return

        session_id = opponent_analyses[0]['session_id']

        # Delete existing stats for this session
        delete_query = text("""
            DELETE FROM opponent_session_stats
            WHERE session_id = :session_id
        """)
        self.db.execute(delete_query, {"session_id": session_id})

        # Insert new stats
        insert_query = text("""
            INSERT INTO opponent_session_stats (
                session_id, opponent_name, hands_observed,
                vpip_pct, pfr_pct, three_bet_pct, fold_to_three_bet_pct,
                cbet_flop_pct, fold_to_cbet_flop_pct,
                vpip_vs_gto, three_bet_vs_gto, fold_to_3bet_vs_gto, cbet_vs_gto,
                tendency_summary, exploits
            ) VALUES (
                :session_id, :opponent_name, :hands_observed,
                :vpip_pct, :pfr_pct, :three_bet_pct, :fold_to_three_bet_pct,
                :cbet_flop_pct, :fold_to_cbet_flop_pct,
                :vpip_vs_gto, :three_bet_vs_gto, :fold_to_3bet_vs_gto, :cbet_vs_gto,
                :tendency_summary, :exploits
            )
        """)

        for analysis in opponent_analyses:
            vpip = analysis.get('vpip_pct', 0) or 0
            three_bet = analysis.get('three_bet_pct', 0) or 0
            fold_to_3bet = analysis.get('fold_to_three_bet_pct', 0) or 0
            cbet = analysis.get('cbet_flop_pct', 0) or 0

            self.db.execute(insert_query, {
                "session_id": analysis['session_id'],
                "opponent_name": analysis['opponent_name'],
                "hands_observed": analysis['hands_observed'],
                "vpip_pct": vpip,
                "pfr_pct": analysis.get('pfr_pct', 0) or 0,
                "three_bet_pct": three_bet,
                "fold_to_three_bet_pct": fold_to_3bet,
                "cbet_flop_pct": cbet,
                "fold_to_cbet_flop_pct": analysis.get('fold_to_cbet_flop_pct', 0) or 0,
                "vpip_vs_gto": vpip - self.GTO_BASELINES['vpip'],
                "three_bet_vs_gto": three_bet - self.GTO_BASELINES['three_bet'],
                "fold_to_3bet_vs_gto": fold_to_3bet - self.GTO_BASELINES['fold_to_three_bet'],
                "cbet_vs_gto": cbet - self.GTO_BASELINES['cbet_flop'],
                "tendency_summary": json.dumps(analysis.get('tendencies', {})),
                "exploits": json.dumps(analysis.get('exploits', []))
            })

        self.db.commit()
