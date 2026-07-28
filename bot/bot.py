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

# Archivio avvertimenti  {guild_id: {user_id: [motivo, ...]}}
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

# Configurazione benvenuto  {guild_id: {channel_id, message}}
WELCOME_FILE = "bot/welcome.json"

def load_welcome():
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE) as f:
            return json.load(f)
    return {}

def save_welcome(data):
    with open(WELCOME_FILE, "w") as f:
        json.dump(data, f, indent=2)

welcome_db = load_welcome()

# ── Intents & Bot ─────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members         = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ── Helpers ───────────────────────────────────────────────────────────────────
def mod_embed(title, description, color=discord.Color.blurple()):
    return discord.Embed(title=title, description=description, color=color)

def success(msg):    return mod_embed("✅ Successo",    msg, discord.Color.green())
def error(msg):      return mod_embed("❌ Errore",      msg, discord.Color.red())
def info(msg):       return mod_embed("ℹ️ Info",        msg, discord.Color.blurple())
def warn_embed(msg): return mod_embed("⚠️ Avvertimento", msg, discord.Color.yellow())

# ── Events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Connesso come {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=f"{PREFIX}help"))

@bot.event
async def on_member_join(member):
    gid = str(member.guild.id)
    cfg = welcome_db.get(gid)
    if not cfg:
        return
    channel = member.guild.get_channel(int(cfg["channel_id"]))
    if not channel:
        return
    msg = cfg["message"].replace("{user}", member.mention) \
                        .replace("{username}", member.display_name) \
                        .replace("{server}", member.guild.name) \
                        .replace("{count}", str(member.guild.member_count))
    embed = discord.Embed(
        title=f"👋 Benvenuto su {member.guild.name}!",
        description=msg,
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Membro #{member.guild.member_count}")
    await channel.send(embed=embed)

@bot.event
async def on_command_error(ctx, exc):
    if isinstance(exc, commands.MissingPermissions):
        await ctx.send(embed=error("Non hai i permessi necessari per usare questo comando."))
    elif isinstance(exc, commands.BotMissingPermissions):
        await ctx.send(embed=error("Non ho i permessi necessari per eseguire questa azione."))
    elif isinstance(exc, commands.MemberNotFound):
        await ctx.send(embed=error("Membro non trovato. Menzionalo o usa il suo ID."))
    elif isinstance(exc, commands.MissingRequiredArgument):
        await ctx.send(embed=error(f"Argomento mancante: `{exc.param.name}`.\nUsa `{PREFIX}help {ctx.command}` per vedere l'utilizzo."))
    elif isinstance(exc, commands.BadArgument):
        await ctx.send(embed=error("Argomento non valido."))
    else:
        raise exc

# ── .help ─────────────────────────────────────────────────────────────────────
@bot.command(name="help")
async def help_cmd(ctx, comando: str = None):
    """Mostra tutti i comandi o i dettagli di un comando specifico."""
    if comando:
        cmd = bot.get_command(comando)
        if not cmd:
            return await ctx.send(embed=error(f"Comando `{PREFIX}{comando}` non trovato."))
        embed = discord.Embed(
            title=f"{PREFIX}{cmd.name}",
            description=cmd.help or "Nessuna descrizione.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Utilizzo", value=f"`{PREFIX}{cmd.name} {cmd.signature}`", inline=False)
        return await ctx.send(embed=embed)

    embed = discord.Embed(
        title="🛡️ Bot di Moderazione",
        description=f"Tutti i comandi usano il prefisso `{PREFIX}`.\nUsa `{PREFIX}help <comando>` per i dettagli.",
        color=discord.Color.blurple()
    )
    gruppi = {
        "👤 Membri":   ["ban", "kick", "warn"],
        "🔇 Muto":     ["mute", "unmute"],
        "🎭 Ruoli":    ["pex", "depex"],
        "💬 Canale":   ["clear", "lock", "unlock"],
        "📢 Messaggi": ["say", "embed"],
        "👋 Benvenuto":["setwelcome", "welcomeoff", "testwelcome"],
    }
    for gruppo, cmds in gruppi.items():
        value = "\n".join(
            f"`{PREFIX}{c}` — {bot.get_command(c).help or 'Nessuna descrizione.'}"
            for c in cmds if bot.get_command(c)
        )
        embed.add_field(name=gruppo, value=value or "—", inline=False)
    embed.set_footer(text=f"Bot creato da {bot.user.name}")
    await ctx.send(embed=embed)

# ── .ban ──────────────────────────────────────────────────────────────────────
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban_cmd(ctx, membro: discord.Member, *, motivo: str = "Nessun motivo fornito"):
    """Banna un membro dal server.
    Utilizzo: .ban @utente [motivo]"""
    if membro == ctx.author:
        return await ctx.send(embed=error("Non puoi bannare te stesso."))
    if membro.top_role >= ctx.author.top_role:
        return await ctx.send(embed=error("Non puoi bannare qualcuno con un ruolo uguale o superiore al tuo."))
    await membro.ban(reason=f"{ctx.author}: {motivo}", delete_message_days=0)
    await ctx.send(embed=success(f"**{membro}** è stato bannato.\n**Motivo:** {motivo}"))

# ── .kick ─────────────────────────────────────────────────────────────────────
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick_cmd(ctx, membro: discord.Member, *, motivo: str = "Nessun motivo fornito"):
    """Espelle un membro dal server.
    Utilizzo: .kick @utente [motivo]"""
    if membro == ctx.author:
        return await ctx.send(embed=error("Non puoi espellere te stesso."))
    if membro.top_role >= ctx.author.top_role:
        return await ctx.send(embed=error("Non puoi espellere qualcuno con un ruolo uguale o superiore al tuo."))
    await membro.kick(reason=f"{ctx.author}: {motivo}")
    await ctx.send(embed=success(f"**{membro}** è stato espulso.\n**Motivo:** {motivo}"))

# ── .mute ─────────────────────────────────────────────────────────────────────
@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def mute_cmd(ctx, membro: discord.Member, durata: str = "10m", *, motivo: str = "Nessun motivo fornito"):
    """Silenzia un membro. Esempi di durata: 10m, 1h, 1d (max 28d).
    Utilizzo: .mute @utente [durata] [motivo]"""
    if membro == ctx.author:
        return await ctx.send(embed=error("Non puoi silenziare te stesso."))
    if membro.top_role >= ctx.author.top_role:
        return await ctx.send(embed=error("Non puoi silenziare qualcuno con un ruolo uguale o superiore al tuo."))

    unità = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    u = durata[-1].lower()
    if u not in unità or not durata[:-1].isdigit():
        return await ctx.send(embed=error("Durata non valida. Usa `s`, `m`, `h` o `d` (es. `10m`, `2h`, `1d`)."))
    secondi = int(durata[:-1]) * unità[u]
    if secondi > 28 * 86400:
        return await ctx.send(embed=error("La durata massima del muto è 28 giorni."))

    fino_a = discord.utils.utcnow() + timedelta(seconds=secondi)
    await membro.timeout(fino_a, reason=f"{ctx.author}: {motivo}")
    await ctx.send(embed=success(f"**{membro}** è stato silenziato per **{durata}**.\n**Motivo:** {motivo}"))

# ── .unmute ───────────────────────────────────────────────────────────────────
@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def unmute_cmd(ctx, membro: discord.Member, *, motivo: str = "Nessun motivo fornito"):
    """Rimuove il silenziamento da un membro.
    Utilizzo: .unmute @utente [motivo]"""
    if not membro.is_timed_out():
        return await ctx.send(embed=info(f"**{membro}** non è attualmente silenziato."))
    await membro.timeout(None, reason=f"{ctx.author}: {motivo}")
    await ctx.send(embed=success(f"**{membro}** è stato de-silenziato.\n**Motivo:** {motivo}"))

# ── .warn ─────────────────────────────────────────────────────────────────────
@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn_cmd(ctx, membro: discord.Member, *, motivo: str = "Nessun motivo fornito"):
    """Avverte un membro e registra l'avvertimento.
    Utilizzo: .warn @utente [motivo]"""
    gid = str(ctx.guild.id)
    uid = str(membro.id)
    warnings_db.setdefault(gid, {}).setdefault(uid, []).append(motivo)
    save_warnings(warnings_db)
    totale = len(warnings_db[gid][uid])
    try:
        await membro.send(embed=warn_embed(
            f"Hai ricevuto un avvertimento su **{ctx.guild.name}**.\n**Motivo:** {motivo}\n**Avvertimenti totali:** {totale}"
        ))
    except discord.Forbidden:
        pass
    await ctx.send(embed=warn_embed(
        f"**{membro}** ha ricevuto un avvertimento. Totale: **{totale}**\n**Motivo:** {motivo}"
    ))

@bot.command(name="warnings")
@commands.has_permissions(kick_members=True)
async def warnings_cmd(ctx, membro: discord.Member):
    """Elenca tutti gli avvertimenti di un membro.
    Utilizzo: .warnings @utente"""
    gid = str(ctx.guild.id)
    uid = str(membro.id)
    warns = warnings_db.get(gid, {}).get(uid, [])
    if not warns:
        return await ctx.send(embed=info(f"**{membro}** non ha avvertimenti."))
    embed = discord.Embed(
        title=f"⚠️ Avvertimenti di {membro}",
        color=discord.Color.yellow()
    )
    for i, w in enumerate(warns, 1):
        embed.add_field(name=f"Avvertimento #{i}", value=w, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="clearwarns")
@commands.has_permissions(kick_members=True)
async def clearwarns_cmd(ctx, membro: discord.Member):
    """Cancella tutti gli avvertimenti di un membro.
    Utilizzo: .clearwarns @utente"""
    gid = str(ctx.guild.id)
    uid = str(membro.id)
    if gid in warnings_db and uid in warnings_db[gid]:
        warnings_db[gid][uid] = []
        save_warnings(warnings_db)
    await ctx.send(embed=success(f"Tutti gli avvertimenti di **{membro}** sono stati cancellati."))

# ── .pex ─────────────────────────────────────────────────────────────────────
@bot.command(name="pex")
@commands.has_permissions(manage_roles=True)
@commands.bot_has_permissions(manage_roles=True)
async def pex_cmd(ctx, membro: discord.Member, *, nome_ruolo: str):
    """Assegna un ruolo a un membro.
    Utilizzo: .pex @utente <nome ruolo>"""
    ruolo = discord.utils.find(lambda r: r.name.lower() == nome_ruolo.lower(), ctx.guild.roles)
    if not ruolo:
        return await ctx.send(embed=error(f"Ruolo `{nome_ruolo}` non trovato."))
    if ruolo >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Non posso assegnare un ruolo uguale o superiore al mio."))
    if ruolo in membro.roles:
        return await ctx.send(embed=info(f"**{membro}** ha già il ruolo `{ruolo.name}`."))
    await membro.add_roles(ruolo, reason=f"pex da {ctx.author}")
    await ctx.send(embed=success(f"Il ruolo `{ruolo.name}` è stato assegnato a **{membro}**."))

# ── .depex ────────────────────────────────────────────────────────────────────
@bot.command(name="depex")
@commands.has_permissions(manage_roles=True)
@commands.bot_has_permissions(manage_roles=True)
async def depex_cmd(ctx, membro: discord.Member, *, nome_ruolo: str):
    """Rimuove un ruolo da un membro.
    Utilizzo: .depex @utente <nome ruolo>"""
    ruolo = discord.utils.find(lambda r: r.name.lower() == nome_ruolo.lower(), ctx.guild.roles)
    if not ruolo:
        return await ctx.send(embed=error(f"Ruolo `{nome_ruolo}` non trovato."))
    if ruolo >= ctx.guild.me.top_role:
        return await ctx.send(embed=error("Non posso rimuovere un ruolo uguale o superiore al mio."))
    if ruolo not in membro.roles:
        return await ctx.send(embed=info(f"**{membro}** non ha il ruolo `{ruolo.name}`."))
    await membro.remove_roles(ruolo, reason=f"depex da {ctx.author}")
    await ctx.send(embed=success(f"Il ruolo `{ruolo.name}` è stato rimosso da **{membro}**."))

# ── .clear ────────────────────────────────────────────────────────────────────
@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def clear_cmd(ctx, quantità: int = 10, membro: discord.Member = None):
    """Elimina i messaggi da un canale. Filtra per membro opzionalmente.
    Utilizzo: .clear [quantità=10] [@utente]"""
    if quantità < 1 or quantità > 1000:
        return await ctx.send(embed=error("La quantità deve essere tra 1 e 1000."))
    await ctx.message.delete()
    check = (lambda m: m.author == membro) if membro else None
    eliminati = await ctx.channel.purge(limit=quantità, check=check)
    msg = await ctx.send(embed=success(f"Eliminati **{len(eliminati)}** messaggi{f' di {membro}' if membro else ''}."))
    await asyncio.sleep(4)
    await msg.delete()

# ── .lock ─────────────────────────────────────────────────────────────────────
@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def lock_cmd(ctx, canale: discord.TextChannel = None, *, motivo: str = "Nessun motivo fornito"):
    """Blocca un canale impedendo a @everyone di scrivere.
    Utilizzo: .lock [#canale] [motivo]"""
    canale = canale or ctx.channel
    overwrite = canale.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await canale.set_permissions(ctx.guild.default_role, overwrite=overwrite,
                                  reason=f"{ctx.author}: {motivo}")
    await canale.send(embed=mod_embed("🔒 Canale Bloccato",
        f"**{canale.mention}** è stato bloccato.\n**Motivo:** {motivo}", discord.Color.red()))

# ── .unlock ───────────────────────────────────────────────────────────────────
@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def unlock_cmd(ctx, canale: discord.TextChannel = None, *, motivo: str = "Nessun motivo fornito"):
    """Sblocca un canale ripristinando la scrittura per @everyone.
    Utilizzo: .unlock [#canale] [motivo]"""
    canale = canale or ctx.channel
    overwrite = canale.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = None
    await canale.set_permissions(ctx.guild.default_role, overwrite=overwrite,
                                  reason=f"{ctx.author}: {motivo}")
    await canale.send(embed=mod_embed("🔓 Canale Sbloccato",
        f"**{canale.mention}** è stato sbloccato.\n**Motivo:** {motivo}", discord.Color.green()))

# ── .say ──────────────────────────────────────────────────────────────────────
@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say_cmd(ctx, canale: discord.TextChannel = None, *, messaggio: str):
    """Fa inviare un messaggio al bot in un canale.
    Utilizzo: .say [#canale] <messaggio>"""
    await ctx.message.delete()
    destinazione = canale or ctx.channel
    await destinazione.send(messaggio)

# ── .embed ────────────────────────────────────────────────────────────────────
@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def embed_cmd(ctx, canale: discord.TextChannel = None, titolo: str = None, *, descrizione: str = None):
    """Invia un embed personalizzato. Metti il titolo tra virgolette se ha spazi.
    Utilizzo: .embed [#canale] \"Titolo\" <descrizione>"""
    await ctx.message.delete()
    destinazione = canale or ctx.channel
    if not titolo and not descrizione:
        return await ctx.send(embed=error("Fornisci almeno un titolo o una descrizione.\nUtilizzo: `.embed [#canale] \"Titolo\" Descrizione`"))
    embed = discord.Embed(
        title=titolo or discord.Embed.Empty,
        description=descrizione or discord.Embed.Empty,
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Inviato da {ctx.author.display_name}")
    await destinazione.send(embed=embed)

# ── .setwelcome ───────────────────────────────────────────────────────────────
@bot.command(name="setwelcome")
@commands.has_permissions(manage_guild=True)
async def setwelcome_cmd(ctx, canale: discord.TextChannel, *, messaggio: str = "Benvenuto nel server, {user}! 🎉"):
    """Imposta il canale e il messaggio di benvenuto. Usa {user}, {username}, {server}, {count}.
    Utilizzo: .setwelcome #canale [messaggio]"""
    gid = str(ctx.guild.id)
    welcome_db[gid] = {"channel_id": str(canale.id), "message": messaggio}
    save_welcome(welcome_db)
    anteprima = messaggio.replace("{user}", ctx.author.mention) \
                         .replace("{username}", ctx.author.display_name) \
                         .replace("{server}", ctx.guild.name) \
                         .replace("{count}", str(ctx.guild.member_count))
    await ctx.send(embed=success(f"Canale di benvenuto impostato su {canale.mention}!\n\n**Anteprima:**\n{anteprima}"))

# ── .welcomeoff ───────────────────────────────────────────────────────────────
@bot.command(name="welcomeoff")
@commands.has_permissions(manage_guild=True)
async def welcomeoff_cmd(ctx):
    """Disabilita i messaggi di benvenuto per questo server.
    Utilizzo: .welcomeoff"""
    gid = str(ctx.guild.id)
    if gid in welcome_db:
        del welcome_db[gid]
        save_welcome(welcome_db)
    await ctx.send(embed=success("I messaggi di benvenuto sono stati disabilitati."))

# ── .testwelcome ──────────────────────────────────────────────────────────────
@bot.command(name="testwelcome")
@commands.has_permissions(manage_guild=True)
async def testwelcome_cmd(ctx):
    """Invia un messaggio di benvenuto di prova per vedere l'anteprima.
    Utilizzo: .testwelcome"""
    gid = str(ctx.guild.id)
    cfg = welcome_db.get(gid)
    if not cfg:
        return await ctx.send(embed=error("Nessun messaggio di benvenuto impostato. Usa prima `.setwelcome #canale <messaggio>`."))
    canale = ctx.guild.get_channel(int(cfg["channel_id"]))
    if not canale:
        return await ctx.send(embed=error("Il canale di benvenuto configurato non esiste più. Esegui di nuovo `.setwelcome`."))
    msg = cfg["message"].replace("{user}", ctx.author.mention) \
                        .replace("{username}", ctx.author.display_name) \
                        .replace("{server}", ctx.guild.name) \
                        .replace("{count}", str(ctx.guild.member_count))
    embed = discord.Embed(
        title=f"👋 Benvenuto su {ctx.guild.name}!",
        description=msg,
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Membro #{ctx.guild.member_count} — ⚠️ Questo è un test")
    await canale.send(embed=embed)
    await ctx.send(embed=info(f"Messaggio di benvenuto di test inviato in {canale.mention}!"))

# ── Run ───────────────────────────────────────────────────────────────────────
if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN non impostato. Aggiungilo come segreto con il nome DISCORD_TOKEN."
    )

bot.run(TOKEN)
