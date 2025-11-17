"""
Unit tests for PokerStars hand history parser.

Tests parser functionality including metadata extraction, action parsing,
and boolean flag calculation.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from backend.parser import PokerStarsParser, Street, ActionType


class TestPokerStarsParser:
    """Tests for PokerStars hand history parser"""

    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return PokerStarsParser()

    @pytest.fixture
    def sample_hand_text(self):
        """Sample hand history text for testing"""
        return """PokerStars Hand #123456789012: Hold'em No Limit ($0.25/$0.50 USD) - 2025/11/17 10:30:15 ET
Table 'Andromeda V' 6-max Seat #1 is the button
Seat 1: Player1 ($50.00 in chips)
Seat 2: Player2 ($75.50 in chips)
Seat 3: Player3 ($100.00 in chips)
Seat 4: Player4 ($62.25 in chips)
Seat 5: Player5 ($88.75 in chips)
Seat 6: Player6 ($55.00 in chips)
Player2: posts small blind $0.25
Player3: posts big blind $0.50
*** HOLE CARDS ***
Player4: folds
Player5: folds
Player6: raises $1.50 to $2.00
Player1: folds
Player2: folds
Player3: calls $1.50
*** FLOP *** [Ah 7c 3d]
Player3: checks
Player6: bets $3.00
Player3: calls $3.00
*** TURN *** [Ah 7c 3d] [Ks]
Player3: checks
Player6: bets $7.50
Player3: folds
Uncalled bet ($7.50) returned to Player6
Player6 collected $9.75 from pot
Player6: doesn't show hand
*** SUMMARY ***
Total pot $10.25 | Rake $0.50
Board [Ah 7c 3d Ks]
Seat 1: Player1 (button) folded before Flop (didn't bet)
Seat 2: Player2 (small blind) folded before Flop
Seat 3: Player3 (big blind) folded on the Turn
Seat 4: Player4 folded before Flop (didn't bet)
Seat 5: Player5 folded before Flop (didn't bet)
Seat 6: Player6 collected ($9.75)
"""

    def test_parse_hand_metadata(self, parser, sample_hand_text):
        """Test parsing of hand header metadata"""
        hand = parser.parse_single_hand(sample_hand_text)

        assert hand is not None
        assert hand.hand_id == 123456789012
        assert hand.stake_level == "NL50"
        assert hand.game_type == "6-max"
        assert hand.table_name == "Andromeda V"
        assert hand.button_seat == 1
        assert isinstance(hand.timestamp, datetime)

    def test_parse_players(self, parser, sample_hand_text):
        """Test player extraction and position assignment"""
        hand = parser.parse_single_hand(sample_hand_text)

        assert len(hand.players) == 6

        # Check specific players
        player1 = hand.get_player("Player1")
        assert player1 is not None
        assert player1.position == "BTN"
        assert player1.starting_stack == Decimal("50.00")

        player2 = hand.get_player("Player2")
        assert player2.position == "SB"

        player3 = hand.get_player("Player3")
        assert player3.position == "BB"

    def test_parse_actions(self, parser, sample_hand_text):
        """Test action parsing"""
        hand = parser.parse_single_hand(sample_hand_text)

        # Should have multiple actions
        assert len(hand.actions) > 0

        # Check blind posts
        blind_actions = [a for a in hand.actions
                        if a.action_type in [ActionType.POST_SB, ActionType.POST_BB]]
        assert len(blind_actions) == 2

        # Check preflop actions
        preflop_actions = [a for a in hand.actions if a.street == Street.PREFLOP]
        assert len(preflop_actions) > 0

        # Check Player6 raised preflop
        player6_raise = next((a for a in preflop_actions
                              if a.player_name == "Player6" and a.action_type == ActionType.RAISE),
                            None)
        assert player6_raise is not None
        assert player6_raise.amount == Decimal("2.00")

    def test_board_cards(self, parser, sample_hand_text):
        """Test board card extraction"""
        hand = parser.parse_single_hand(sample_hand_text)

        assert 'flop' in hand.board_cards
        assert hand.board_cards['flop'] == 'Ah 7c 3d'

        assert 'turn' in hand.board_cards
        assert hand.board_cards['turn'] == 'Ks'

    def test_pot_and_rake(self, parser, sample_hand_text):
        """Test pot and rake extraction"""
        hand = parser.parse_single_hand(sample_hand_text)

        assert hand.pot_size == Decimal("10.25")
        assert hand.rake == Decimal("0.50")

    def test_player_flags_vpip(self, parser, sample_hand_text):
        """Test VPIP flag calculation"""
        hand = parser.parse_single_hand(sample_hand_text)

        # Player6 raised - should have VPIP
        player6_flags = hand.player_flags["Player6"]
        assert player6_flags.vpip is True

        # Player3 called - should have VPIP
        player3_flags = hand.player_flags["Player3"]
        assert player3_flags.vpip is True

        # Player4 folded - should not have VPIP
        player4_flags = hand.player_flags["Player4"]
        assert player4_flags.vpip is False

    def test_player_flags_pfr(self, parser, sample_hand_text):
        """Test PFR flag calculation"""
        hand = parser.parse_single_hand(sample_hand_text)

        # Player6 raised preflop
        player6_flags = hand.player_flags["Player6"]
        assert player6_flags.pfr is True

        # Player3 only called
        player3_flags = hand.player_flags["Player3"]
        assert player3_flags.pfr is False

    def test_player_flags_saw_streets(self, parser, sample_hand_text):
        """Test street visibility flags"""
        hand = parser.parse_single_hand(sample_hand_text)

        # Player3 and Player6 saw flop and turn
        player3_flags = hand.player_flags["Player3"]
        assert player3_flags.saw_flop is True
        assert player3_flags.saw_turn is True
        assert player3_flags.saw_river is False  # Folded on turn

        player6_flags = hand.player_flags["Player6"]
        assert player6_flags.saw_flop is True
        assert player6_flags.saw_turn is True

        # Player4 didn't see flop
        player4_flags = hand.player_flags["Player4"]
        assert player4_flags.saw_flop is False

    def test_player_flags_cbet(self, parser, sample_hand_text):
        """Test continuation bet flags"""
        hand = parser.parse_single_hand(sample_hand_text)

        # Player6 was preflop raiser and bet flop (cbet)
        player6_flags = hand.player_flags["Player6"]
        assert player6_flags.cbet_opportunity_flop is True
        assert player6_flags.cbet_made_flop is True

    def test_profit_loss(self, parser, sample_hand_text):
        """Test profit/loss calculation"""
        hand = parser.parse_single_hand(sample_hand_text)

        # Player6 won
        player6_flags = hand.player_flags["Player6"]
        assert player6_flags.won_hand is True
        assert player6_flags.profit_loss > Decimal("0")

        # Player3 lost
        player3_flags = hand.player_flags["Player3"]
        assert player3_flags.won_hand is False
        assert player3_flags.profit_loss < Decimal("0")

    def test_parse_file(self, parser, tmp_path):
        """Test parsing a complete file"""
        # Create temporary test file
        test_file = tmp_path / "test_hands.txt"
        test_file.write_text("""PokerStars Hand #123456789012: Hold'em No Limit ($0.25/$0.50 USD) - 2025/11/17 10:30:15 ET
Table 'Andromeda V' 6-max Seat #1 is the button
Seat 1: Player1 ($50.00 in chips)
Seat 2: Player2 ($75.50 in chips)
Player2: posts small blind $0.25
Player1: posts big blind $0.50
*** HOLE CARDS ***
Player2: folds
Player1 collected $0.50 from pot
*** SUMMARY ***
Total pot $0.50 | Rake $0.00
Seat 1: Player1 (big blind) collected ($0.50)
Seat 2: Player2 (small blind) folded before Flop
""")

        result = parser.parse_file(str(test_file))

        assert result.total_hands == 1
        assert result.successful == 1
        assert result.failed == 0
        assert len(result.hands) == 1


if __name__ == "__main__":
    # Simple test run
    parser = PokerStarsParser()

    sample_file = "backend/tests/data/sample_hands.txt"
    try:
        result = parser.parse_file(sample_file)
        print(f"\nParsing Results:")
        print(f"Total hands: {result.total_hands}")
        print(f"Successful: {result.successful}")
        print(f"Failed: {result.failed}")

        if result.hands:
            print(f"\nFirst hand:")
            hand = result.hands[0]
            print(f"  Hand ID: {hand.hand_id}")
            print(f"  Stakes: {hand.stake_level}")
            print(f"  Players: {len(hand.players)}")
            print(f"  Actions: {len(hand.actions)}")

            print(f"\n  Player flags:")
            for player_name, flags in hand.player_flags.items():
                print(f"    {player_name}: VPIP={flags.vpip}, PFR={flags.pfr}, "
                      f"Saw Flop={flags.saw_flop}, P/L=${flags.profit_loss}")

    except FileNotFoundError:
        print(f"Sample file not found: {sample_file}")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
