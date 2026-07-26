import discord
from discord.ext import commands
import os
import json
import asyncio
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
TOKEN   = os.getenv("DISCORD_TOKEN")
PREFIX  = "."

# Persistent warnings store  {guild_id: {user_id: [reason, ...]}}
WARNINGS_FILE = "bot/warnings.json"

def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE) as f:
            return json.load(f)
    return {}

def save_warnings(data):
    with open(WARNINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

warnings_db = load_warnings()

# ── Intents & Bot ─────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members   = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ── Helpers ───────────────────────────────────────────────────────────────────
def mod_embed(title, description, color=discord.Color.blurple()):
    embed = discord.Embed(title=title, description=description, color=color)
    return embed

def success(msg):  return mod_embed("✅ Success",  msg, discord.Color.green())
def error(msg):    return mod_embed("❌ Error",    msg, discord.Color.red())
def info(msg):     return mod_embed("ℹ️ Info",     msg, discord.Color.blurple())
def warn_embed(msg): return mod_embed("⚠️ Warning", msg, discord.Color.yellow())

# ── Events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=f"{PREFIX}help"))

@bot.event
async def on_command_error(ctx, exc):
    if isinstance(exc, commands.MissingPermissions):
        await ctx.send(embed=error("You don't have permission to use this command."))
    elif isinstance(exc, commands.BotMissingPermissions):
        await ctx.send(embed=error("I don't have the required permissions to do that."))
    elif isinstance(exc, commands.MemberNotFound):
        await ctx.send(embed=error("Member not found. Mention them or use their ID."))
    elif isinstance(exc, commands.MissingRequiredArgument):
        await ctx.send(embed=error(f"Missing argument: `{exc.param.name}`.\nUse `{PREFIX}help {ctx.command}` for usage."))
    elif isinstance(exc, commands.BadArgument):
        await ctx.send(embed=error("Invalid argument provided."))
    else:
        raise exc

# ── .help ─────────────────────────────────────────────────────────────────────
@bot.command(name="help")
async def help_cmd(ctx, command_name: str = None):
    """Show all commands or details for a specific command."""
    if command_name:
        cmd = bot.get_command(command_name)
        if not cmd:
            return await ctx.send(embed=error(f"Command `{PREFIX}{command_name}` not found."))
        embed = discord.Embed(
            title=f"{PREFIX}{cmd.name}",
            description=cmd.help or "No description.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Usage", value=f"`{PREFIX}{cmd.name} {cmd.signature}`", inline=False)
        return await ctx.send(embed=embed)

    embed = discord.Embed(
        title="🛡️ Moderation Bot",
        description=f"All commands use the `{PREFIX}` prefix.\nUse `{PREFIX}help <command>` for details.",
        color=discord.Color.blurple()
    )
    groups = {
        "👤 Member": ["ban", "kick", "warn"],
        "🔇 Mute":   ["mute", "unmute"],
        "🎭 Roles":  ["pex", "depex"],
        "💬 Channel":["clear", "lock", "unlock"],
        "📢 Message":["say", "embed"],
    }
    for group, cmds in groups.items():
        value = "\n".join(
            f"`{PREFIX}{c}` — {bot.get_command(c).help or 'No description.'}"
            for c in cmds if bot.get_command(c)
        )
        embed.add_field(name=group, value=value or "—", inline=False)
    embed.set_footer(text=f"Bot by {bot.user.name}")
    await ctx.send(embed=embed)

# ── .ban ──────────────────────────────────────────────────────────────────────
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member from the server.
    Usage: .ban @user [reason]"""
    if member == ctx.author:
        return await ctx.send(embed=error("You cannot ban yourself."))
    if member.top_role >= ctx.author.top_role:
        return await ctx.send(embed=error("You cannot ban someone with an equal or higher role."))
    await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=0)
    await ctx.send(embed=success(f"**{member}** has been banned.\n**Reason:** {reason}"))

# ── .kick ─────────────────────────────────────────────────────────────────────
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member from the server.
    Usage: .kick @user [reason]"""
    if member == ctx.author:
        return await ctx.send(embed=error("You cannot kick yourself."))
    if member.top_role >= ctx.author.top_role:
        return await ctx.send(embed=error("You cannot kick someone with an equal or higher role."))
    await member.kick(reason=f"{ctx.author}: {reason}")
    await ctx.send(embed=success(f"**{member}** has been kicked.\n**Reason:** {reason}"))

# ── .mute ─────────────────────────────────────────────────────────────────────
@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def mute_cmd(ctx, member: discord.Member, duration: str = "10m", *, reason: str = "No reason provided"):
    """Timeout (mute) a member. Duration examples: 10m, 1h, 1d (max 28d).
    Usage: .mute @user [duration] [reason]"""
    if member == ctx.author:
        return await ctx.send(embed=error("You cannot mute yourself."))
    if member.top_role >= ctx.author.top_role:
        return await ctx.send(embed=error("You cannot mute someone with an equal or higher role."))

    # Parse duration
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit  = duration[-1].lower()
    if unit not in units or not duration[:-1].isdigit():
        return await ctx.send(embed=error("Invalid duration. Use `s`, `m`, `h`, or `d` (e.g. `10m`, `2h`, `1d`)."))
    seconds = int(duration[:-1]) * units[unit]
    if seconds > 28 * 86400:
        return await ctx.send(embed=error("Maximum mute duration is 28 days."))

    until = discord.utils.utcnow() + timedelta(seconds=seconds)
    await member.timeout(until, reason=f"{ctx.author}: {reason}")
    await ctx.send(embed=success(f"**{member}** has been muted for **{duration}**.\n**Reason:** {reason}"))

# ── .unmute ───────────────────────────────────────────────────────────────────
@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def unmute_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Remove a timeout (unmute) from a member.
    Usage: .unmute @user [reason]"""
    if not member.is_timed_out():
        return await ctx.send(embed=info(f"**{member}** is not currently muted."))
    await member.timeout(None, reason=f"{ctx.author}: {reason}")
    await ctx.send(embed=success(f"**{member}** has been unmuted.\n**Reason:** {reason}"))

# ── .warn ─────────────────────────────────────────────────────────────────────
@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Warn a member and record it. Use .warn list @user to view warnings.
    Usage: .warn @user [reason]  |  .warn list @user"""
    gid = str(ctx.guild.id)
    uid = str(member.id)
    warnings_db.setdefault(gid, {}).setdefault(uid, []).append(reason)
    save_warnings(warnings_db)
    count = len(warnings_db[gid][uid])
    try:
        await member.send(embed=warn_embed(
            f"You have been warned in **{ctx.guild.name}**.\n**Reason:** {reason}\n**Total warnings:** {count}"
        ))
    except discord.Forbidden:
        pass
    await ctx.send(embed=warn_embed(
        f"**{member}** has been warned. Total warnings: **{count}**\n**Reason:** {reason}"
    ))

@bot.command(name="warnings")
@commands.has_permissions(kick_members=True)
async def warnings_cmd(ctx, member: discord.Member):
    """List all warnings for a member.
    Usage: .warnings @user"""
    gid = str(ctx.guild.id)
    uid = str(member.id)
    warns = warnings_db.get(gid, {}).get(uid, [])
    if not warns:
        return await ctx.send(embed=info(f"**{member}** has no warnings."))
    embed = discord.Embed(
        title=f"⚠️ Warnings for {member}",
        color=discord.Color.yellow()
    )
    for i, w in enumerate(warns, 1):
        embed.add_field(name=f"Warning #{i}", value=w, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="clearwarns")
@commands.has_permissions(kick_members=True)
async def clearwarns_cmd(ctx, member: discord.Member):
    """Clear all warnings for a member.
    Usage: .clearwarns @user"""
    gid = str(ctx.guild.id)
    uid = str(member.id)
    if gid in warnings_db and uid in warnings_db[gid]:
        warnings_db[gid][uid] = []
        save_warnings(warnings_db)
    await ctx.send(embed=success(f"Cleared all warnings for **{member}**."))

# ── .pex ─────────────────────────────────────────────────────────────────────
@bot.command(name="pex")
@commands.has_permissions(manage_roles=True)
@commands.bot_has_permissions(manage_roles=True)
async def pex_cmd(ctx, member: discord.Member, *, role_name: str):
    """Give a role to a member.
    Usage: .pex @user <role name>"""
    role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), ctx.guild.roles)
    if not role:
        return await ctx.send(embed=error(f"Role `{role_name}` not found."))
    if role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("I cannot assign a role equal to or above my own."))
    if role in member.roles:
        return await ctx.send(embed=info(f"**{member}** already has the `{role.name}` role."))
    await member.add_roles(role, reason=f"pex by {ctx.author}")
    await ctx.send(embed=success(f"Gave **{member}** the `{role.name}` role."))

# ── .depex ────────────────────────────────────────────────────────────────────
@bot.command(name="depex")
@commands.has_permissions(manage_roles=True)
@commands.bot_has_permissions(manage_roles=True)
async def depex_cmd(ctx, member: discord.Member, *, role_name: str):
    """Remove a role from a member.
    Usage: .depex @user <role name>"""
    role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), ctx.guild.roles)
    if not role:
        return await ctx.send(embed=error(f"Role `{role_name}` not found."))
    if role >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("I cannot remove a role equal to or above my own."))
    if role not in member.roles:
        return await ctx.send(embed=info(f"**{member}** doesn't have the `{role.name}` role."))
    await member.remove_roles(role, reason=f"depex by {ctx.author}")
    await ctx.send(embed=success(f"Removed the `{role.name}` role from **{member}**."))

# ── .clear ────────────────────────────────────────────────────────────────────
@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def clear_cmd(ctx, amount: int = 10, member: discord.Member = None):
    """Delete messages from a channel. Optionally filter by member.
    Usage: .clear [amount=10] [@user]"""
    if amount < 1 or amount > 1000:
        return await ctx.send(embed=error("Amount must be between 1 and 1000."))
    await ctx.message.delete()
    check = (lambda m: m.author == member) if member else None
    deleted = await ctx.channel.purge(limit=amount, check=check)
    msg = await ctx.send(embed=success(f"Deleted **{len(deleted)}** message(s){f' from {member}' if member else ''}."))
    await asyncio.sleep(4)
    await msg.delete()

# ── .lock ─────────────────────────────────────────────────────────────────────
@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def lock_cmd(ctx, channel: discord.TextChannel = None, *, reason: str = "No reason provided"):
    """Lock a channel so @everyone cannot send messages.
    Usage: .lock [#channel] [reason]"""
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite,
                                   reason=f"{ctx.author}: {reason}")
    await channel.send(embed=mod_embed("🔒 Channel Locked",
        f"**{channel.mention}** has been locked.\n**Reason:** {reason}", discord.Color.red()))

# ── .unlock ───────────────────────────────────────────────────────────────────
@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def unlock_cmd(ctx, channel: discord.TextChannel = None, *, reason: str = "No reason provided"):
    """Unlock a channel to restore messaging for @everyone.
    Usage: .unlock [#channel] [reason]"""
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = None  # reset to inherit
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite,
                                   reason=f"{ctx.author}: {reason}")
    await channel.send(embed=mod_embed("🔓 Channel Unlocked",
        f"**{channel.mention}** has been unlocked.\n**Reason:** {reason}", discord.Color.green()))

# ── .say ──────────────────────────────────────────────────────────────────────
@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say_cmd(ctx, channel: discord.TextChannel = None, *, message: str):
    """Make the bot send a message to a channel.
    Usage: .say [#channel] <message>"""
    await ctx.message.delete()
    target = channel or ctx.channel
    await target.send(message)

# ── .embed ────────────────────────────────────────────────────────────────────
@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def embed_cmd(ctx, channel: discord.TextChannel = None, title: str = None, *, description: str = None):
    """Send a custom embed. Put multi-word title in quotes.
    Usage: .embed [#channel] \"Title\" <description>"""
    await ctx.message.delete()
    target = channel or ctx.channel
    if not title and not description:
        return await ctx.send(embed=error("Provide at least a title or description.\nUsage: `.embed [#channel] \"Title\" Description`"))
    embed = discord.Embed(
        title=title or discord.Embed.Empty,
        description=description or discord.Embed.Empty,
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Sent by {ctx.author.display_name}")
    await target.send(embed=embed)

# ── Run ───────────────────────────────────────────────────────────────────────
if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is not set. Add it as a secret named DISCORD_TOKEN."
    )

bot.run(TOKEN)
