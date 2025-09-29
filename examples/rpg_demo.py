#!/usr/bin/env python3
"""
Simple RPG Demo - Loading XML Prompt Example

This example demonstrates how to load an RPG Game Master prompt from an XML file
using the tinyagent prompt loader functionality.
"""

from pathlib import Path

from tinyagent import ReactAgent, tool

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not installed, skip


@tool
def roll_dice(sides: int = 20, modifier: int = 0) -> str:
    """
    Roll a dice with specified number of sides and add modifier.

    Parameters
    ----------
    sides : int
        Number of sides on the dice (default: 20)
    modifier : int
        Modifier to add to the roll (default: 0)

    Returns
    -------
    str
        The dice roll result
    """
    import random

    roll = random.randint(1, sides)
    total = roll + modifier

    if modifier == 0:
        return f"Rolled d{sides}: {roll}"
    else:
        modifier_str = f"+{modifier}" if modifier > 0 else str(modifier)
        return f"Rolled d{sides}{modifier_str}: {roll} {modifier_str} = {total}"


@tool
def ship_status() -> str:
    """
    Get current starship status report.

    Returns
    -------
    str
        Ship systems status
    """
    return """STARSHIP STATUS REPORT:

Hull Integrity: 85%
Shield Strength: 92%
Weapon Systems: 100%
Engine Power: 78%
Cargo Capacity: 45% used

Note: Engine efficiency slightly reduced - recommend maintenance at next port."""


def main():
    """Run the RPG demo with XML prompt loading."""

    # Get the path to the RPG prompt file
    current_dir = Path(__file__).parent
    rpg_prompt_path = current_dir / "prompts" / "example-rpg.xml"

    print("Starfarer Chronicles RPG Demo")
    print("=" * 40)

    # Check if the prompt file exists
    if not rpg_prompt_path.exists():
        print(f"Error: RPG prompt file not found at {rpg_prompt_path}")
        print("Make sure the examples/prompts/example-rpg.xml file exists.")
        return

    print(f"Loading RPG prompt from: {rpg_prompt_path}")

    try:
        # Create the agent with the XML prompt file
        agent = ReactAgent(
            prompt_file=str(rpg_prompt_path),
            tools=[roll_dice, ship_status],
            model="gpt-4o-mini",  # Use a cost-effective model for demo
        )

        # Debug: Print the system prompt to see if tools are included
        print(f"[DEBUG] System prompt preview: {agent._system_prompt[:500]}...")
        print(f"[DEBUG] Full system prompt length: {len(agent._system_prompt)} characters")
        print(f"[DEBUG] Available tools: {list(agent._tool_map.keys())}")

        print("RPG Game Master initialized successfully!")
        print("\nAvailable tools:")
        print("  • roll_dice - Roll dice with modifiers")
        print("  • ship_status - Check starship systems")

        # Start the RPG session
        print("\n" + "=" * 50)
        print("WELCOME TO STARFARER CHRONICLES")
        print("=" * 50)

        # Initial scenario
        scenario = """
        Captain, you've just received a distress signal from the mining colony on Kepler-442b.
        The signal is weak and fragmented, but you can make out: "...under attack...unknown vessels...
        need immediate assistance..."

        Your ship, the UES Horizon, is currently in orbit around the gas giant Kepler-442c,
        about 2 hours away at maximum warp.

        What are your orders?
        """

        print(scenario)

        # Get player input and let the agent respond
        while True:
            print("\n" + "-" * 30)
            user_input = input("Your action: ").strip()

            if user_input.lower() in ["quit", "exit", "end"]:
                print("\nThanks for playing Starfarer Chronicles!")
                break

            if not user_input:
                continue

            print("\nGame Master:")
            try:
                response = agent.run(user_input, max_steps=5)
                print(response)
            except Exception as e:
                print(f"Error: {e}")
                print("The Game Master encountered an issue. Please try again.")

    except Exception as e:
        print(f"Failed to initialize RPG agent: {e}")
        print("Make sure you have set up your OpenAI API key.")


if __name__ == "__main__":
    main()
