"""
One-time setup script: creates a persistent Browser Use profile and opens
a live browser so you can log into Google manually. After login, the profile
saves cookies so all future browser agent runs skip authentication.

Usage:
    python -m backend.agents.browser.setup_profile

Prerequisites:
    - BROWSER_USE_API_KEY set in .env or environment
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from browser_use_sdk.v3 import AsyncBrowserUse


async def main():
    api_key = os.getenv("BROWSER_USE_API_KEY", "").strip()
    if not api_key:
        print("ERROR: BROWSER_USE_API_KEY is not set in .env")
        print("Get one at https://cloud.browser-use.com/settings")
        return

    client = AsyncBrowserUse()

    # Create a named profile
    profile_name = input("Profile name (default: google-workspace): ").strip()
    if not profile_name:
        profile_name = "google-workspace"

    profile = await client.profiles.create(name=profile_name)
    print(f"\nProfile created: {profile.id}")
    print(f"Save this as GOOGLE_PROFILE_ID in your .env file.\n")

    # Start a session with the profile so we can log in
    session = await client.sessions.create(
        profile_id=profile.id,
        keep_alive=True,
    )

    print(f"Live browser URL: {session.live_url}")
    print()
    print("1. Open the URL above in your browser")
    print("2. Log into your Google account (Gmail, Sheets, etc.)")
    print("3. Complete any 2FA prompts")
    print("4. Come back here and press Enter when done")
    print()
    input("Press Enter after you've logged in...")

    # Stop the session — this saves cookies to the profile
    await client.sessions.stop(session.id)

    print()
    print("Profile saved! Add this to your .env:")
    print(f"  GOOGLE_PROFILE_ID={profile.id}")
    print()
    print("The browser agent will now reuse this profile for all actions.")


if __name__ == "__main__":
    asyncio.run(main())
