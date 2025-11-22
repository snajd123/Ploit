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
    hero_name: Optional[str] = None
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

    # Get hero stats if provided
    hero_stats = None
    hero_analysis = None
    if request.hero_name:
        hero_player = db.query(PlayerStats).filter(
            PlayerStats.player_name == request.hero_name
        ).first()

        if hero_player:
            hero_stats = {
                'player_name': hero_player.player_name,
                'player_type': hero_player.player_type,
                'total_hands': hero_player.total_hands,
                'vpip_pct': hero_player.vpip_pct,
                'pfr_pct': hero_player.pfr_pct,
                'three_bet_pct': hero_player.three_bet_pct,
                'cbet_flop_pct': hero_player.cbet_flop_pct,
                'wtsd_pct': hero_player.wtsd_pct,
                'aggression_factor': hero_player.af,
                'exploitability_index': hero_player.exploitability_index
            }

            # Get hero's deviations from GTO using REAL GTO data
            hero_analysis = gto_service.compare_player_to_gto(
                player_name=request.hero_name,  # Pass hero name for real GTO data
                player_stats={  # Fallback traditional stats if no GTO data
                    'vpip_pct': hero_player.vpip_pct,
                    'pfr_pct': hero_player.pfr_pct,
                    'three_bet_pct': hero_player.three_bet_pct,
                    'fold_to_three_bet_pct': hero_player.fold_to_three_bet_pct,
                    'cbet_flop_pct': hero_player.cbet_flop_pct,
                    'fold_to_cbet_flop_pct': hero_player.fold_to_cbet_flop_pct,
                    'wtsd_pct': hero_player.wtsd_pct
                }
            )

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

        # Get exploit analysis using REAL GTO data
        analysis = gto_service.compare_player_to_gto(
            player_name=opponent_name,  # Pass player name for real GTO data lookup
            player_stats={  # Fallback traditional stats if no GTO data
                'vpip_pct': player.vpip_pct,
                'pfr_pct': player.pfr_pct,
                'three_bet_pct': player.three_bet_pct,
                'fold_to_three_bet_pct': player.fold_to_three_bet_pct,
                'cbet_flop_pct': player.cbet_flop_pct,
                'fold_to_cbet_flop_pct': player.fold_to_cbet_flop_pct,
                'wtsd_pct': player.wtsd_pct
            }
        )

        # Get top 3 exploits (prioritize by EV loss if available, else by deviation)
        exploitable_devs = [d for d in analysis['deviations'] if d.get('exploitable', False)]
        # Sort by EV loss if available (real GTO data), otherwise by absolute deviation
        exploitable_devs.sort(
            key=lambda x: x.get('ev_loss', x['abs_deviation']),
            reverse=True
        )
        top_3 = exploitable_devs[:3]

        # Use full exploit recommendations for actionable, precise instructions
        top_exploit_strs = [
            dev['exploit_recommendation']
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
                'AF': f"{player.af:.2f}" if player.af else "N/A",
                'AFQ': f"{player.afq:.1f}%" if player.afq else "N/A",
                'BB/100': f"{player.bb_per_100:+.1f}" if player.bb_per_100 is not None else "N/A",
                'C-Bet': f"{player.cbet_flop_pct:.1f}%" if player.cbet_flop_pct else "N/A",
                'WTSD': f"{player.wtsd_pct:.1f}%" if player.wtsd_pct else "N/A"
            }
        ))

    # Generate AI strategy using Claude
    prompt = f"""Generate a comprehensive pre-game poker strategy for an upcoming {request.game_type} session at {request.stakes or 'unknown stakes'}.

"""

    # Add hero analysis if provided
    if hero_stats:
        prompt += f"""YOUR PROFILE ({hero_stats['player_name']}):
- Player Type: {hero_stats['player_type'] or 'Unknown'}
- Total Hands: {hero_stats['total_hands']}
"""
        # Format stats safely, handling None values
        vpip = f"{hero_stats['vpip_pct']:.1f}%" if hero_stats['vpip_pct'] is not None else "N/A"
        pfr = f"{hero_stats['pfr_pct']:.1f}%" if hero_stats['pfr_pct'] is not None else "N/A"
        three_bet = f"{hero_stats['three_bet_pct']:.1f}%" if hero_stats['three_bet_pct'] is not None else "N/A"
        cbet = f"{hero_stats['cbet_flop_pct']:.1f}%" if hero_stats['cbet_flop_pct'] is not None else "N/A"
        wtsd = f"{hero_stats['wtsd_pct']:.1f}%" if hero_stats['wtsd_pct'] is not None else "N/A"

        prompt += f"- VPIP: {vpip} | PFR: {pfr} | 3Bet: {three_bet}\n"
        prompt += f"- CBet: {cbet} | WTSD: {wtsd}\n"

        if hero_stats['exploitability_index'] is not None:
            prompt += f"- Exploitability Index: {hero_stats['exploitability_index']:.1f}/100\n"

        prompt += "\nYOUR TENDENCIES:\n"

        if hero_analysis:
            hero_devs = [d for d in hero_analysis['deviations'] if d.get('exploitable', False)]
            hero_devs.sort(key=lambda x: x['abs_deviation'], reverse=True)
            for dev in hero_devs[:3]:
                prompt += f"- {dev['stat']}: {dev['exploit_direction']} ({dev['deviation']:+.1f}%)\n"

        prompt += "\n"

    prompt += """OPPONENTS ANALYSIS:
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
Please provide a PERSONALIZED strategy """

    if hero_stats:
        prompt += f"""that considers {hero_stats['player_name']}'s playing style and tendencies. """

    prompt += """Include:
1. SESSION SUMMARY (2-3 sentences about the table composition"""

    if hero_stats:
        prompt += f""" and how it matches up with {hero_stats['player_name']}'s style"""

    prompt += """)
2. TABLE DYNAMICS (how the table will likely play, aggression levels, who will clash"""

    if hero_stats:
        prompt += f""", and specifically how opponents will react to {hero_stats['player_name']}'s tendencies"""

    prompt += """)
3. OVERALL STRATEGY (your general approach for this specific table"""

    if hero_stats:
        prompt += f""", tailored to {hero_stats['player_name']}'s strengths and weaknesses"""

    prompt += """)
4. FOCUS AREAS (3-5 bullet points of key things to focus on"""

    if hero_stats:
        prompt += f""", considering {hero_stats['player_name']}'s style"""

    prompt += """)
5. QUICK TIPS (3-5 actionable tips for this session"""

    if hero_stats:
        prompt += f""", personalized for {hero_stats['player_name']}"""

    prompt += """)

Format as JSON with keys: session_summary, table_dynamics, overall_strategy, focus_areas (array), quick_tips (array)
"""

    try:
        # Query Claude API directly (without database tools) for cleaner JSON response
        from anthropic import Anthropic
        from backend.config import get_settings
        import json

        settings = get_settings()
        client = Anthropic(api_key=settings.anthropic_api_key)

        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4096,
            system="You are a professional poker strategy advisor. You MUST respond with ONLY valid JSON - no explanatory text, no markdown formatting, just the JSON object itself. Do not include ```json``` code blocks.",
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract text from response
        strategy_text = ""
        for block in response.content:
            if block.type == "text":
                strategy_text += block.text

        # Parse JSON from response
        # First try direct JSON parsing (since we asked for pure JSON)
        strategy_json = None
        try:
            strategy_json = json.loads(strategy_text.strip())
        except json.JSONDecodeError:
            # If that fails, try extracting from markdown code block
            if '```json' in strategy_text:
                json_start = strategy_text.find('```json') + 7
                json_end = strategy_text.find('```', json_start)
                strategy_json = json.loads(strategy_text[json_start:json_end].strip())
            elif '{' in strategy_text:
                # Extract the JSON object from the text
                json_start = strategy_text.find('{')
                json_end = strategy_text.rfind('}') + 1
                strategy_json = json.loads(strategy_text[json_start:json_end])

        if not strategy_json:
            # Fallback if all parsing attempts fail
            raise ValueError("Failed to parse JSON from Claude response")

        return PreGameStrategyResponse(
            session_summary=strategy_json['session_summary'],
            table_dynamics=strategy_json['table_dynamics'],
            overall_strategy=strategy_json['overall_strategy'],
            opponent_summaries=opponent_summaries,
            focus_areas=strategy_json['focus_areas'],
            quick_tips=strategy_json['quick_tips']
        )

    except Exception as e:
        # Log the error for debugging
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating strategy: {str(e)}")
        logger.error(traceback.format_exc())

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

    # Get exploit analysis using REAL GTO data
    analysis = gto_service.compare_player_to_gto(
        player_name=player_name,
        player_stats={
            'vpip_pct': player.vpip_pct,
            'pfr_pct': player.pfr_pct,
            'three_bet_pct': player.three_bet_pct,
            'fold_to_three_bet_pct': player.fold_to_three_bet_pct,
            'cbet_flop_pct': player.cbet_flop_pct,
            'fold_to_cbet_flop_pct': player.fold_to_cbet_flop_pct,
            'wtsd_pct': player.wtsd_pct
        }
    )

    # Get top 5 exploits sorted by EV loss (GTO-based) or deviation (fallback)
    exploitable_devs = [d for d in analysis['deviations'] if d.get('exploitable', False)]

    # Sort by EV loss if GTO-based, otherwise by deviation
    if exploitable_devs and exploitable_devs[0].get('is_gto_based', False):
        exploitable_devs.sort(key=lambda x: abs(x.get('ev_loss', 0)), reverse=True)
    else:
        exploitable_devs.sort(key=lambda x: x['abs_deviation'], reverse=True)

    top_5 = exploitable_devs[:5]

    # Helper function to get explicit exploitation strategy
    def get_explicit_exploit(dev):
        # If this is GTO-based data, use the detailed exploit recommendation
        if dev.get('is_gto_based', False):
            return dev.get('exploit_recommendation', dev.get('exploit_direction', 'No specific exploit'))

        # Otherwise, use old hardcoded mapping for traditional stats
        stat = dev['stat']
        direction = dev['exploit_direction']
        deviation = dev['deviation']

        # Map stat names to explicit strategies
        exploit_strategies = {
            'VPIP': {
                'positive': f"→ They play too many hands. 3-bet them more aggressively, especially from position. Value bet thinner post-flop.",
                'negative': f"→ They play too tight. Steal their blinds frequently and avoid paying them off with marginal hands."
            },
            'PFR': {
                'positive': f"→ They raise too often. Call more in position to see flops and outplay them post-flop. Trap with strong hands.",
                'negative': f"→ They're too passive preflop. Attack their limps with raises. When they do raise, respect it more."
            },
            'CBET_FLOP': {
                'positive': f"→ They c-bet too much. Float the flop more often and attack on later streets when they check.",
                'negative': f"→ They give up too easily. Bet when they check and continue barreling on multiple streets."
            },
            'FOLD_TO_CBET_FLOP': {
                'positive': f"→ They fold too much to c-bets. Continuation bet aggressively with your entire range, especially on dry boards.",
                'negative': f"→ They're a calling station. Only c-bet for value and give up with pure air. Avoid bluffing them."
            },
            'FOLD_TO_3BET': {
                'positive': f"→ They fold too much to 3-bets. 3-bet them with a polarized range, adding more bluffs. Print money.",
                'negative': f"→ They don't fold to 3-bets. Only 3-bet for value and be prepared to see flops. Tighten up your 3-betting range."
            },
            '3BET': {
                'positive': f"→ They 3-bet too much. Trap them with strong hands by flatting. 4-bet bluff them occasionally.",
                'negative': f"→ They never 3-bet. Open wider from late position and respect their 3-bets when they finally make one."
            },
            'WTSD': {
                'positive': f"→ They go to showdown too often. Value bet thin and avoid bluffing - they'll call you down with weak hands.",
                'negative': f"→ They fold too much on later streets. Barrel more often and apply pressure with bluffs on turn and river."
            }
        }

        # Get the appropriate strategy
        is_positive = deviation > 0
        exploit_key = 'positive' if is_positive else 'negative'
        strategy = exploit_strategies.get(stat, {}).get(exploit_key, direction)

        return strategy

    # Helper function to determine severity from GTO data
    def get_severity(dev):
        if dev.get('is_gto_based', False):
            # For GTO-based, use EV loss to determine severity
            ev_loss = abs(dev.get('ev_loss', 0))
            if ev_loss > 2.0:
                return 'critical'
            elif ev_loss > 1.0:
                return 'major'
            elif ev_loss > 0.5:
                return 'moderate'
            else:
                return 'minor'
        else:
            # For traditional stats, use existing severity
            return dev.get('severity', 'moderate')

    return {
        'player_name': player_name,
        'player_type': player.player_type,
        'total_hands': player.total_hands,
        'exploitability_index': player.exploitability_index,
        'key_stats': {
            'VPIP': f"{player.vpip_pct:.1f}%" if player.vpip_pct else "N/A",
            'PFR': f"{player.pfr_pct:.1f}%" if player.pfr_pct else "N/A",
            '3Bet': f"{player.three_bet_pct:.1f}%" if player.three_bet_pct else "N/A",
            'AF': f"{player.af:.2f}" if player.af else "N/A",
            'AFQ': f"{player.afq:.1f}%" if player.afq else "N/A",
            'BB/100': f"{player.bb_per_100:+.1f}" if player.bb_per_100 is not None else "N/A",
            'C-Bet': f"{player.cbet_flop_pct:.1f}%" if player.cbet_flop_pct else "N/A",
            'Fold to 3Bet': f"{player.fold_to_three_bet_pct:.1f}%" if player.fold_to_three_bet_pct else "N/A",
            'WTSD': f"{player.wtsd_pct:.1f}%" if player.wtsd_pct else "N/A"
        },
        'top_exploits': [
            {
                'stat': dev['stat'],
                'exploit': get_explicit_exploit(dev),
                'deviation': f"{dev['deviation']:+.1f}%",
                'severity': get_severity(dev),
                'ev_loss': f"{dev.get('ev_loss', 0):.2f} BB" if dev.get('is_gto_based', False) else None,
                'is_gto_based': dev.get('is_gto_based', False)
            }
            for dev in top_5
        ],
        'total_ev': analysis.get('total_estimated_ev', 0)
    }
