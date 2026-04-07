"""
main.py

This is the entry point.
Flow:
User -> Agent -> ArmorClaw -> Execute or Block
"""

from pathlib import Path

from .agent import agent_loop
from .armorclaw import ArmorClaw
from .executor import execute


def main():
    # Load policy engine.
    policy_file = Path(__file__).parent / "policies.yaml"
    armor = ArmorClaw(str(policy_file))

    # Take user input.
    user_input = input("Enter command: ")

    # Agent creates a structured decision.
    decision = agent_loop(user_input)

    # ArmorClaw checks if the action is safe.
    allowed, reason = armor.check(decision)

    # Execute only if allowed.
    if allowed:
        result = execute(decision)
        print("✅", result)
    else:
        print("❌ Blocked:", reason)


if __name__ == "__main__":
    main()