import discord
from discord.ext import commands
import json
import logging
import os
import aiohttp
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

OPENCODE_SERVER_URL = os.getenv("OPENCODE_SERVER_URL", "http://localhost:4096")
OPENCODE_USERNAME = os.getenv("OPENCODE_USERNAME", "opencode")
OPENCODE_PASSWORD = os.getenv("OPENCODE_SERVER_PASSWORD")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

user_sessions = {}


async def opencode_request(
    method: str, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None
) -> Optional[Any]:
    auth = (
        aiohttp.BasicAuth(OPENCODE_USERNAME, OPENCODE_PASSWORD)
        if OPENCODE_PASSWORD
        else None
    )

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{OPENCODE_SERVER_URL}{path}"

            if method == "GET":
                async with session.get(url, auth=auth, params=params) as response:
                    if response.content_type == "application/json":
                        return await response.json()
                    return await response.text()
            elif method == "POST":
                async with session.post(
                    url, json=data, auth=auth, params=params
                ) as response:
                    if response.content_type == "application/json":
                        return await response.json()
                    return await response.text()
            elif method == "DELETE":
                async with session.delete(url, auth=auth) as response:
                    if response.content_type == "application/json":
                        return await response.json()
                    return await response.text()
            elif method == "PATCH":
                async with session.patch(url, json=data, auth=auth) as response:
                    if response.content_type == "application/json":
                        return await response.json()
                    return await response.text()

    except aiohttp.ClientError as e:
        logger.error(f"OpenCode API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None


async def get_or_create_session(user_id: str) -> Optional[str]:
    if user_id in user_sessions:
        return user_sessions[user_id]

    sessions = await opencode_request("GET", "/session")
    if isinstance(sessions, list) and len(sessions) > 0:
        session_id = sessions[0].get("id") if isinstance(sessions[0], dict) else None
        if session_id:
            user_sessions[user_id] = session_id
            return session_id

    new_session = await opencode_request(
        "POST", "/session", {"title": f"Discord User {user_id}"}
    )
    if isinstance(new_session, dict) and "id" in new_session:
        session_id = new_session["id"]
        user_sessions[user_id] = session_id
        return session_id

    return None


async def send_message_to_opencode(
    session_id: str, message_content: str
) -> Optional[Dict]:
    payload = {"parts": [{"type": "text", "text": message_content}]}

    result = await opencode_request(
        "POST", f"/session/{session_id}/message", data=payload
    )
    if isinstance(result, dict):
        return result
    return None


@bot.event
async def on_ready():
    logger.info(f"{bot.user} has connected to Discord!")
    logger.info(f"Connected to OpenCode server at {OPENCODE_SERVER_URL}")

    health = await opencode_request("GET", "/global/health")
    if health:
        logger.info(f"OpenCode server health: {health}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="Type to interact"
        )
    )


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    user_id = str(message.author.id)
    session_id = await get_or_create_session(user_id)

    if not session_id:
        embed = discord.Embed(
            title="❌ Error",
            description="Failed to create or retrieve session with OpenCode server.",
            color=discord.Color.red(),
        )
        await message.channel.send(embed=embed)
        return

    embed = discord.Embed(
        title="💭 Thinking...",
        description="Sending your request to OpenCode...",
        color=discord.Color.yellow(),
    )
    status_msg = await message.channel.send(embed=embed)

    try:
        response = await send_message_to_opencode(session_id, message.content)

        if response and isinstance(response, dict) and "parts" in response:
            content_parts = []

            for part in response["parts"]:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_content = part.get("text", "")
                    if text_content:
                        content_parts.append(text_content)

            full_response = "\n".join(content_parts).strip()

            if len(full_response) > 4000:
                full_response = full_response[:4000] + "\n\n... (truncated)"

            embed = discord.Embed(
                description=full_response,
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc),
            )
            if bot.user and bot.user.display_avatar:
                embed.set_author(name="OpenCode", icon_url=bot.user.display_avatar.url)
            embed.set_footer(text=f"Session: {session_id[:8]}...")

            await status_msg.edit(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Received unexpected response from OpenCode.",
                color=discord.Color.red(),
            )
            await status_msg.edit(embed=embed)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(e)}",
            color=discord.Color.red(),
        )
        await status_msg.edit(embed=embed)


@bot.command(name="help")
async def help_command(ctx: commands.Context):
    embed = discord.Embed(
        title="🤖 OpenCode Discord Bot",
        description="A Discord bot that connects to OpenCode in server mode",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="How it works",
        value="Just type your question or request, and I'll send it to OpenCode for processing.",
        inline=False,
    )
    embed.add_field(
        name="Commands",
        value="`!help` - Show this help\n`!session` - Show current session info\n`!newsession` - Start a new session",
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command(name="session")
async def show_session(ctx: commands.Context):
    user_id = str(ctx.author.id)
    session_id = await get_or_create_session(user_id)

    if session_id:
        embed = discord.Embed(
            title="📋 Current Session",
            description=f"Your OpenCode session ID: `{session_id}`",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Error",
            description="Failed to retrieve session.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)


@bot.command(name="newsession")
async def new_session(ctx: commands.Context):
    user_id = str(ctx.author.id)

    new_session = await opencode_request(
        "POST",
        "/session",
        {
            "title": f"Discord User {user_id} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        },
    )

    if isinstance(new_session, dict) and "id" in new_session:
        session_id = new_session["id"]
        user_sessions[user_id] = session_id

        embed = discord.Embed(
            title="✨ New Session Created",
            description=f"Your new OpenCode session ID: `{session_id}`",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Error",
            description="Failed to create new session.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: {round(bot.latency * 1000)}ms",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set!")
        return

    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
