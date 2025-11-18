"""
API endpoints for pre-game strategy generation.

Provides strategy recommendations for upcoming poker sessions.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.services.gto_service import GTOService
from backend.services.claude_service import ClaudeService
from backend.database import get_db
from backend.models.database_models import PlayerStats

router = APIRouter(prefix="/api/strategy", tags=["Strategy"])


# Request/Response models
class PreGameStrategyRequest(BaseModel):
    """Request for pre-game strategy"""
    opponent_names: List[str]
    stakes: Optional[str] = None
    game_type: Optional[str] = "6-max Cash"


class OpponentSummary(BaseModel):
    """Quick opponent summary"""
    player_name: str
    player_type: Optional[str] = None
    total_hands: int
    exploitability_index: Optional[float] = None
    top_exploits: List[str]
    key_stats: dict


class PreGameStrategyResponse(BaseModel):
    """Pre-game strategy response"""
    session_summary: str
    table_dynamics: str
    overall_strategy: str
    opponent_summaries: List[OpponentSummary]
    focus_areas: List[str]
    quick_tips: List[str]


@router.post("/pre-game", response_model=PreGameStrategyResponse)
async def generate_pre_game_strategy(
    request: PreGameStrategyRequest,
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive pre-game strategy.

    Analyzes opponents and provides detailed strategy recommendations
    including table dynamics, opponent exploits, and focus areas.
    """
    gto_service = GTOService(db)
    opponent_summaries = []
    all_exploits = []

    # Analyze each opponent
    for opponent_name in request.opponent_names:
        player = db.query(PlayerStats).filter(
            PlayerStats.player_name == opponent_name
        ).first()

        if not player:
            # Unknown opponent
            opponent_summaries.append(OpponentSummary(
                player_name=opponent_name,
                player_type="UNKNOWN",
                total_hands=0,
                exploitability_index=None,
                top_exploits=["No data available - play ABC poker"],
                key_stats={}
            ))
            continue

        # Get exploit analysis
        analysis = gto_service.compare_player_to_gto({
            'vpip_pct': player.vpip_pct,
            'pfr_pct': player.pfr_pct,
            'three_bet_pct': player.three_bet_pct,
            'fold_to_three_bet_pct': player.fold_to_three_bet_pct,
            'cbet_flop_pct': player.cbet_flop_pct,
            'fold_to_cbet_flop_pct': player.fold_to_cbet_flop_pct,
            'wtsd_pct': player.wtsd_pct
        })

        # Get top 3 exploits
        exploitable_devs = [d for d in analysis['deviations'] if d.get('exploitable', False)]
        exploitable_devs.sort(key=lambda x: x['abs_deviation'], reverse=True)
        top_3 = exploitable_devs[:3]

        top_exploit_strs = [
            f"{dev['stat']}: {dev['exploit_direction']} ({dev['deviation']:+.1f}%)"
            for dev in top_3
        ]

        all_exploits.extend(top_3)

        opponent_summaries.append(OpponentSummary(
            player_name=opponent_name,
            player_type=player.player_type,
            total_hands=player.total_hands,
            exploitability_index=player.exploitability_index,
            top_exploits=top_exploit_strs if top_exploit_strs else ["Playing close to baseline"],
            key_stats={
                'VPIP': f"{player.vpip_pct:.1f}%" if player.vpip_pct else "N/A",
                'PFR': f"{player.pfr_pct:.1f}%" if player.pfr_pct else "N/A",
                '3Bet': f"{player.three_bet_pct:.1f}%" if player.three_bet_pct else "N/A",
                'WTSD': f"{player.wtsd_pct:.1f}%" if player.wtsd_pct else "N/A"
            }
        ))

    # Generate AI strategy using Claude
    prompt = f"""Generate a comprehensive pre-game poker strategy for an upcoming {request.game_type} session at {request.stakes or 'unknown stakes'}.

OPPONENTS ANALYSIS:
"""

    for opp in opponent_summaries:
        prompt += f"\n{opp.player_name}:"
        prompt += f"\n- Player Type: {opp.player_type or 'Unknown'}"
        prompt += f"\n- Hands: {opp.total_hands}"
        if opp.exploitability_index:
            prompt += f"\n- Exploitability: {opp.exploitability_index:.1f}/100"
        prompt += f"\n- Key Stats: {opp.key_stats}"
        prompt += f"\n- Top Exploits: {', '.join(opp.top_exploits)}"
        prompt += "\n"

    prompt += """
Please provide:
1. SESSION SUMMARY (2-3 sentences about the table composition)
2. TABLE DYNAMICS (how the table will likely play, aggression levels, who will clash)
3. OVERALL STRATEGY (your general approach for this specific table)
4. FOCUS AREAS (3-5 bullet points of key things to focus on)
5. QUICK TIPS (3-5 actionable tips for this session)

Format as JSON with keys: session_summary, table_dynamics, overall_strategy, focus_areas (array), quick_tips (array)
"""

    try:
        # Query Claude for strategy
        claude_service = ClaudeService(db)
        claude_response = claude_service.query(
            user_query=prompt,
            conversation_history=[]
        )

        if not claude_response.get('success'):
            raise HTTPException(status_code=500, detail="Failed to generate strategy")

        # Parse Claude response
        import json
        strategy_text = claude_response['response']

        # Try to extract JSON from response
        if '```json' in strategy_text:
            json_start = strategy_text.find('```json') + 7
            json_end = strategy_text.find('```', json_start)
            strategy_json = json.loads(strategy_text[json_start:json_end])
        elif '{' in strategy_text:
            json_start = strategy_text.find('{')
            json_end = strategy_text.rfind('}') + 1
            strategy_json = json.loads(strategy_text[json_start:json_end])
        else:
            # Fallback if Claude doesn't return JSON
            strategy_json = {
                'session_summary': 'Mixed table with exploitable opponents',
                'table_dynamics': strategy_text[:200],
                'overall_strategy': 'Play exploitative poker while maintaining solid fundamentals',
                'focus_areas': ['Exploit opponent tendencies', 'Position awareness', 'Aggression control'],
                'quick_tips': ['3-bet light against over-folders', 'Value bet thinner vs calling stations']
            }

        return PreGameStrategyResponse(
            session_summary=strategy_json['session_summary'],
            table_dynamics=strategy_json['table_dynamics'],
            overall_strategy=strategy_json['overall_strategy'],
            opponent_summaries=opponent_summaries,
            focus_areas=strategy_json['focus_areas'],
            quick_tips=strategy_json['quick_tips']
        )

    except Exception as e:
        # Fallback strategy if Claude fails
        return PreGameStrategyResponse(
            session_summary=f"Table with {len(opponent_summaries)} tracked opponents",
            table_dynamics="Mixed player types - adjust based on opponent tendencies",
            overall_strategy="Play exploitative poker while maintaining fundamentals. Target the most exploitable opponents.",
            opponent_summaries=opponent_summaries,
            focus_areas=[
                "Exploit opponent tendencies identified in the data",
                "Maintain position awareness",
                "Adjust aggression based on opponent types",
                "Focus on high EV spots against weak players"
            ],
            quick_tips=[
                "Target over-folders with more bluffs",
                "Value bet thinner against calling stations",
                "Avoid bluffing into stations",
                "3-bet more against weak players in position"
            ]
        )


@router.get("/quick-lookup/{player_name}")
async def quick_lookup(
    player_name: str,
    db: Session = Depends(get_db)
):
    """
    Quick opponent lookup for fast reference.

    Returns essential info and top exploits only.
    """
    player = db.query(PlayerStats).filter(
        PlayerStats.player_name == player_name
    ).first()

    if not player:
        raise HTTPException(
            status_code=404,
            detail=f"Player not found: {player_name}"
        )

    gto_service = GTOService(db)

    # Get exploit analysis
    analysis = gto_service.compare_player_to_gto({
        'vpip_pct': player.vpip_pct,
        'pfr_pct': player.pfr_pct,
        'three_bet_pct': player.three_bet_pct,
        'fold_to_three_bet_pct': player.fold_to_three_bet_pct,
        'cbet_flop_pct': player.cbet_flop_pct,
        'fold_to_cbet_flop_pct': player.fold_to_cbet_flop_pct,
        'wtsd_pct': player.wtsd_pct
    })

    # Get top 5 exploits
    exploitable_devs = [d for d in analysis['deviations'] if d.get('exploitable', False)]
    exploitable_devs.sort(key=lambda x: x['abs_deviation'], reverse=True)
    top_5 = exploitable_devs[:5]

    return {
        'player_name': player_name,
        'player_type': player.player_type,
        'total_hands': player.total_hands,
        'exploitability_index': player.exploitability_index,
        'key_stats': {
            'VPIP': f"{player.vpip_pct:.1f}%" if player.vpip_pct else "N/A",
            'PFR': f"{player.pfr_pct:.1f}%" if player.pfr_pct else "N/A",
            '3Bet': f"{player.three_bet_pct:.1f}%" if player.three_bet_pct else "N/A",
            'Fold to 3Bet': f"{player.fold_to_three_bet_pct:.1f}%" if player.fold_to_three_bet_pct else "N/A",
            'WTSD': f"{player.wtsd_pct:.1f}%" if player.wtsd_pct else "N/A"
        },
        'top_exploits': [
            {
                'stat': dev['stat'],
                'exploit': dev['exploit_direction'],
                'deviation': f"{dev['deviation']:+.1f}%",
                'severity': dev['severity']
            }
            for dev in top_5
        ],
        'total_ev': analysis.get('total_estimated_ev', 0)
    }
