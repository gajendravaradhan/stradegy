#!/usr/bin/env python3
"""Discord Bot Diagnostic Tool - Run this to verify your Discord setup"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stradegy.config import settings


async def diagnose():
    print("=" * 60)
    print("DISCORD BOT DIAGNOSTIC")
    print("=" * 60)
    
    # Check config values
    print("\n1. CHECKING CONFIGURATION...")
    print(f"   Bot Token present: {bool(settings.discord_bot_token)}")
    print(f"   Token length: {len(settings.discord_bot_token)} chars")
    print(f"   Channel IDs: {settings.discord_channel_ids}")
    print(f"   Guild IDs: {settings.discord_guild_ids}")
    print(f"   User ID: {settings.discord_user_id}")
    
    if not settings.discord_bot_token:
        print("   ERROR: Bot token is empty!")
        print("   Fix: Add DISCORD_BOT_TOKEN to backend/.env")
        return
        
    if not settings.discord_user_id:
        print("   ERROR: User ID is empty!")
        print("   Fix: Add DISCORD_USER_ID to backend/.env")
        return
    
    # Test Discord API connection
    print("\n2. TESTING DISCORD API CONNECTION...")
    import httpx
    
    client = httpx.AsyncClient(
        headers={"Authorization": f"Bot {settings.discord_bot_token}"},
        timeout=30.0
    )
    
    try:
        # Test 1: Get bot's own info
        resp = await client.get("https://discord.com/api/v10/users/@me")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   Bot Name: {data.get('username')}#{data.get('discriminator', '0')}")
            print(f"   Bot ID: {data.get('id')}")
            print("   Status: Token is VALID")
        elif resp.status_code == 401:
            print("   ERROR: Invalid bot token (401 Unauthorized)")
            print("   Fix: Regenerate token at discord.com/developers/applications")
            return
        else:
            print(f"   ERROR: API returned {resp.status_code}")
            return
            
        # Test 2: Get guilds/servers the bot is in
        print("\n3. CHECKING SERVERS...")
        resp = await client.get("https://discord.com/api/v10/users/@me/guilds")
        if resp.status_code == 200:
            guilds = resp.json()
            print(f"   Bot is in {len(guilds)} server(s):")
            for guild in guilds:
                print(f"   - {guild.get('name')} (ID: {guild.get('id')})")
        else:
            print(f"   ERROR: Could not fetch guilds ({resp.status_code})")
        
        # Test 3: Try to create DM channel
        print("\n4. TESTING DM CHANNEL CREATION...")
        print(f"   Target User ID: {settings.discord_user_id}")
        
        resp = await client.post(
            "https://discord.com/api/v10/users/@me/channels",
            json={"recipient_id": settings.discord_user_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   SUCCESS: DM channel created (ID: {data.get('id')})")
            print("   You should see a DM from the bot in Discord now!")
        elif resp.status_code == 403:
            print("   ERROR: 403 Forbidden - Cannot DM this user")
            print("   Common causes:")
            print("   a) You copied the BOT's ID instead of YOUR ID")
            print("   b) You and the bot don't share a server")
            print("   c) You have 'Allow DMs from server members' disabled")
            print("   d) You blocked the bot")
            print("\n   FIXES:")
            print("   1. In Discord, go to User Settings > Privacy & Safety")
            print("   2. Enable 'Allow direct messages from server members'")
            print("   3. Right-click YOUR name (not the bot's) > Copy User ID")
            print("   4. Update DISCORD_USER_ID in backend/.env")
            print("   5. Make sure the bot is in at least one server with you")
        elif resp.status_code == 429:
            print("   ERROR: Rate limited. Wait a few minutes and try again.")
        else:
            print(f"   ERROR: API returned {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            
        # Test 4: Try to read from configured channels
        print("\n5. TESTING CHANNEL ACCESS...")
        if settings.discord_channel_ids:
            channel_ids = [c.strip() for c in settings.discord_channel_ids.split(",") if c.strip()]
            for channel_id in channel_ids[:3]:  # Test first 3
                resp = await client.get(f"https://discord.com/api/v10/channels/{channel_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"   Channel {channel_id}: OK ({data.get('name', 'unknown')})")
                elif resp.status_code == 403:
                    print(f"   Channel {channel_id}: ACCESS DENIED (403)")
                elif resp.status_code == 404:
                    print(f"   Channel {channel_id}: NOT FOUND (404)")
                else:
                    print(f"   Channel {channel_id}: ERROR {resp.status_code}")
        else:
            print("   No channel IDs configured")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    finally:
        await client.aclose()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(diagnose())
