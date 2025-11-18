"""
GTO King API - Proof of Concept
Test extracting GTO ranges by playing hands and capturing disclosed ranges.
"""

import requests
import json
from typing import Dict, List, Optional


class GTOKingAPI:
    """Interface to GTO King API for range extraction"""

    BASE_URL = "https://gtoking.com/api/play"

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.stack_size = 200  # Track stack size for all requests

    def start_hand(self, stack_size: int = 200) -> Dict:
        """
        Start a new hand.

        Args:
            stack_size: Stack size in small blinds (100BB = 200 small blinds)

        Returns:
            API response with initial game state
        """
        self.stack_size = stack_size  # Store for subsequent actions

        payload = {
            "token": self.token,
            "initialStacks": [stack_size] * 6,  # 6-max: 6 players
            "game_format": "6max"  # 6-max cash game
        }

        response = self.session.post(self.BASE_URL, json=payload)
        response.raise_for_status()

        return response.json()

    def make_action(self, bet: Optional[int] = None) -> Dict:
        """
        Make an action in current hand.

        Args:
            bet: Bet amount (None to check/fold, 0 to fold, >0 to bet/call/raise)

        Returns:
            API response with game state and potentially range disclosure
        """
        payload = {
            "token": self.token,
            "initialStacks": [self.stack_size] * 6,  # 6-max: 6 players
            "game_format": "6max"  # 6-max cash game
        }

        if bet is not None:
            payload["bet"] = bet

        response = self.session.post(self.BASE_URL, json=payload)
        response.raise_for_status()

        return response.json()

    def play_simple_scenario(self) -> Dict:
        """
        Play one complete hand to test range disclosure.

        Scenario: Open from button, see if we get opponent's defense range
        """
        print("=" * 60)
        print("Testing GTO King Range Disclosure")
        print("=" * 60)

        # Start new hand
        print("\n1. Starting new hand...")
        initial = self.start_hand(stack_size=200)  # 100BB
        print(f"   Position: {initial.get('position')} (0=SB, 1=BB)")
        print(f"   Hole cards: {initial.get('hole_cards')}")
        print(f"   History: {initial.get('history')}")
        print(f"   Default bets: {initial.get('default_bets')}")

        # Read the state first to see default bets
        print("\n2. Reading current state...")
        state = self.make_action()  # No bet = just read state
        print(f"   State: {json.dumps(state, indent=2)}")

        # Use default bets if available
        default_bets = state.get('default_bets', [])
        if default_bets:
            print(f"\n3. Making action with default bet: {default_bets[0]}...")
            response = self.make_action(bet=default_bets[0])
            print(f"   Response: {json.dumps(response, indent=2)}")
        else:
            response = state

        # Fold to complete hand
        print("\n4. Folding to complete hand...")
        # Check if we have default bets for folding
        fold_bets = response.get('default_bets', [])
        if fold_bets:
            # Usually first default bet is fold/check
            final = self.make_action(bet=fold_bets[0])
        else:
            # Try -1 for fold
            final = self.make_action(bet=-1)

        # Check for range disclosure
        print("\n" + "=" * 60)
        print("FULL FINAL RESPONSE (looking for range disclosure):")
        print("=" * 60)
        print(json.dumps(final, indent=2))

        return final


def main():
    """Run proof of concept"""
    print("\nGTO King API - Range Extraction PoC")
    print("=" * 60)

    # Get token from user
    token = input("\nEnter your GTO King bot token: ").strip()

    if not token:
        print("Error: Token required")
        return

    try:
        api = GTOKingAPI(token)
        result = api.play_simple_scenario()

        print("\n" + "=" * 60)
        print("ANALYSIS:")
        print("=" * 60)

        # Check what keys are available
        print(f"\nAvailable keys in response: {list(result.keys())}")

        # Look for range-related data
        range_keys = [k for k in result.keys() if 'range' in k.lower()]
        if range_keys:
            print(f"\n✓ Found range-related keys: {range_keys}")
            for key in range_keys:
                print(f"\n{key}:")
                print(json.dumps(result[key], indent=2))
        else:
            print("\n⚠ No obvious 'range' keys found in response")
            print("   Range might be disclosed in a different format")
            print("   Check the full response above for range data")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ API Error: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
