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

# Configurazione addio  {guild_id: {channel_id, message}}
GOODBYE_FILE = "bot/goodbye.json"

def load_goodbye():
    if os.path.exists(GOODBYE_FILE):
        with open(GOODBYE_FILE) as f:
            return json.load(f)
    return {}

def save_goodbye(data):
    with open(GOODBYE_FILE, "w") as f:
        json.dump(data, f, indent=2)

goodbye_db = load_goodbye()

# Configurazione ticket  {guild_id: {support_role_id, category_id, counter}}
TICKETS_FILE = "bot/tickets.json"

def load_tickets():
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE) as f:
            return json.load(f)
    return {}

def save_tickets(data):
    with open(TICKETS_FILE, "w") as f:
        json.dump(data, f, indent=2)

tickets_db = load_tickets()

# ── Ticket UI (pulsante + modal) ───────────────────────────────────────────────
async def _crea_ticket(guild: discord.Guild, autore: discord.Member, motivo: str):
    """Logica comune per creare un canale ticket."""
    gid = str(guild.id)
    cfg = tickets_db.setdefault(gid, {})
    cfg["counter"] = cfg.get("counter", 0) + 1
    save_tickets(tickets_db)
    numero = cfg["counter"]

    nome_canale = f"ticket-{numero:04d}-{autore.name.lower().replace(' ', '-')}"
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        autore:             discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me:           discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    support_role_id = cfg.get("support_role_id")
    support_role = guild.get_role(int(support_role_id)) if support_role_id else None
    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    category = guild.get_channel(int(cfg["category_id"])) if cfg.get("category_id") else None

    canale_ticket = await guild.create_text_channel(
        nome_canale,
        overwrites=overwrites,
        category=category,
        topic=f"Ticket di {autore} | Motivo: {motivo}"
    )

    embed = discord.Embed(
        title=f"🎫 Ticket #{numero:04d}",
        description=(
            f"Ciao {autore.mention}! Il tuo ticket è stato aperto.\n\n"
            f"**Motivo:** {motivo}\n\n"
            "Lo staff ti risponderà presto.\n"
            "Usa `.closeticket` per chiudere questo ticket."
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Aperto da {autore} • {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}")
    content = support_role.mention if support_role else None
    await canale_ticket.send(content=content, embed=embed)
    return canale_ticket


TICKET_CATEGORIE = {
    "premio":    ("🎁 Ritira un premio",              "Vuoi ritirare un premio che hai vinto."),
    "staff":     ("🙋 Candidatura staff",             "Vuoi candidarti per entrare nello staff."),
    "collab":    ("🫂 Collab/Partnership",             "Vuoi proporre una collaborazione o partnership."),
    "report":    ("❌ Segnala un utente",              "Vuoi segnalare un utente che viola le regole."),
    "trusted":   ("✔️ Richiedi Trusted/Super trusted", "Vuoi richiedere il ruolo Trusted o Super trusted."),
}

class TicketModal(discord.ui.Modal):
    descrizione = discord.ui.TextInput(
        label="Descrizione",
        placeholder="Descrivi brevemente il tuo problema...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True,
    )

    def __init__(self, categoria: str):
        label, _ = TICKET_CATEGORIE.get(categoria, ("Ticket", ""))
        super().__init__(title=f"Apri Ticket — {label}")
        self.categoria = categoria

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        label, _ = TICKET_CATEGORIE.get(self.categoria, ("Ticket", ""))
        motivo = f"[{label}] {self.descrizione.value}"
        try:
            canale = await _crea_ticket(interaction.guild, interaction.user, motivo)
            await interaction.followup.send(
                embed=discord.Embed(
                    title="✅ Ticket aperto!",
                    description=f"Il tuo ticket è stato creato in {canale.mention}.",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Errore",
                    description="Non ho i permessi per creare canali.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistente

    @discord.ui.select(
        cls=discord.ui.Select,
        placeholder="📩 Seleziona il tipo di ticket...",
        custom_id="ticket_select_menu",
        options=[
            discord.SelectOption(label=label, value=key, description=desc, emoji=label.split()[0])
            for key, (label, desc) in TICKET_CATEGORIE.items()
        ]
    )
    async def select_ticket(self, interaction: discord.Interaction, select: discord.ui.Select):
        categoria = select.values[0]
        await interaction.response.send_modal(TicketModal(categoria))


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
    bot.add_view(TicketButton())  # registra il pulsante persistente
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
async def on_member_remove(member):
    gid = str(member.guild.id)
    cfg = goodbye_db.get(gid)
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
        title=f"👋 Arrivederci da {member.guild.name}!",
        description=msg,
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Membri rimasti: {member.guild.member_count}")
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
        "👋 Addio":    ["setgoodbye", "goodbyeoff", "testgoodbye"],
        "🎫 Ticket":   ["setupticket", "ticket", "closeticket", "addticket", "removeticket"],
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

# ── .setgoodbye ───────────────────────────────────────────────────────────────
@bot.command(name="setgoodbye")
@commands.has_permissions(manage_guild=True)
async def setgoodbye_cmd(ctx, canale: discord.TextChannel, *, messaggio: str = "Ciao {username}, ci mancherai! 👋"):
    """Imposta il canale e il messaggio di addio. Usa {user}, {username}, {server}, {count}.
    Utilizzo: .setgoodbye #canale [messaggio]"""
    gid = str(ctx.guild.id)
    goodbye_db[gid] = {"channel_id": str(canale.id), "message": messaggio}
    save_goodbye(goodbye_db)
    anteprima = messaggio.replace("{user}", ctx.author.mention) \
                         .replace("{username}", ctx.author.display_name) \
                         .replace("{server}", ctx.guild.name) \
                         .replace("{count}", str(ctx.guild.member_count))
    await ctx.send(embed=success(f"Canale di addio impostato su {canale.mention}!\n\n**Anteprima:**\n{anteprima}"))

# ── .goodbyeoff ───────────────────────────────────────────────────────────────
@bot.command(name="goodbyeoff")
@commands.has_permissions(manage_guild=True)
async def goodbyeoff_cmd(ctx):
    """Disabilita i messaggi di addio per questo server.
    Utilizzo: .goodbyeoff"""
    gid = str(ctx.guild.id)
    if gid in goodbye_db:
        del goodbye_db[gid]
        save_goodbye(goodbye_db)
    await ctx.send(embed=success("I messaggi di addio sono stati disabilitati."))

# ── .testgoodbye ──────────────────────────────────────────────────────────────
@bot.command(name="testgoodbye")
@commands.has_permissions(manage_guild=True)
async def testgoodbye_cmd(ctx):
    """Invia un messaggio di addio di prova per vedere l'anteprima.
    Utilizzo: .testgoodbye"""
    gid = str(ctx.guild.id)
    cfg = goodbye_db.get(gid)
    if not cfg:
        return await ctx.send(embed=error("Nessun messaggio di addio impostato. Usa prima `.setgoodbye #canale <messaggio>`."))
    canale = ctx.guild.get_channel(int(cfg["channel_id"]))
    if not canale:
        return await ctx.send(embed=error("Il canale di addio configurato non esiste più. Esegui di nuovo `.setgoodbye`."))
    msg = cfg["message"].replace("{user}", ctx.author.mention) \
                        .replace("{username}", ctx.author.display_name) \
                        .replace("{server}", ctx.guild.name) \
                        .replace("{count}", str(ctx.guild.member_count))
    embed = discord.Embed(
        title=f"👋 Arrivederci da {ctx.guild.name}!",
        description=msg,
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Membri rimasti: {ctx.guild.member_count} — ⚠️ Questo è un test")
    await canale.send(embed=embed)
    await ctx.send(embed=info(f"Messaggio di addio di test inviato in {canale.mention}!"))

# ── .setupticket ──────────────────────────────────────────────────────────────
@bot.command(name="setupticket")
@commands.has_permissions(manage_guild=True)
@commands.bot_has_permissions(manage_channels=True)
async def setupticket_cmd(ctx, canale: discord.TextChannel = None, ruolo: discord.Role = None):
    """Configura il sistema ticket e invia il pannello in un canale.
    Utilizzo: .setupticket [#canale] [@ruolo_supporto]"""
    gid = str(ctx.guild.id)
    canale = canale or ctx.channel
    tickets_db.setdefault(gid, {})
    if ruolo:
        tickets_db[gid]["support_role_id"] = str(ruolo.id)
    tickets_db[gid].setdefault("counter", 0)
    save_tickets(tickets_db)

    embed = discord.Embed(
        title="🎫 Supporto",
        description=(
            "Hai bisogno di aiuto o vuoi contattare lo staff?\n\n"
            "Clicca il pulsante qui sotto per aprire un ticket privato.\n\n"
            "Il nostro team ti risponderà il prima possibile."
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text=ctx.guild.name)
    await canale.send(embed=embed, view=TicketButton())
    ruolo_txt = f" | Ruolo supporto: {ruolo.mention}" if ruolo else ""
    await ctx.send(embed=success(f"Sistema ticket configurato in {canale.mention}{ruolo_txt}."))

# ── .ticket ───────────────────────────────────────────────────────────────────
@bot.command(name="ticket")
@commands.bot_has_permissions(manage_channels=True)
async def ticket_cmd(ctx, *, motivo: str = "Nessun motivo specificato"):
    """Apre un ticket privato con lo staff.
    Utilizzo: .ticket [motivo]"""
    try:
        canale_ticket = await _crea_ticket(ctx.guild, ctx.author, motivo)
    except discord.Forbidden:
        return await ctx.send(embed=error("Non ho i permessi per creare canali."))
    await ctx.send(embed=success(f"Ticket aperto! Vai in {canale_ticket.mention}"), delete_after=10)
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

# ── .closeticket ──────────────────────────────────────────────────────────────
@bot.command(name="closeticket")
@commands.bot_has_permissions(manage_channels=True)
async def closeticket_cmd(ctx, *, motivo: str = "Nessun motivo"):
    """Chiude il ticket corrente eliminando il canale.
    Utilizzo: .closeticket [motivo]"""
    if not ctx.channel.name.startswith("ticket-"):
        return await ctx.send(embed=error("Questo comando può essere usato solo in un canale ticket."))

    embed = discord.Embed(
        title="🔒 Ticket Chiuso",
        description=f"Ticket chiuso da **{ctx.author}**.\n**Motivo:** {motivo}\n\nIl canale verrà eliminato tra 5 secondi.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)
    await asyncio.sleep(5)
    try:
        await ctx.channel.delete(reason=f"Ticket chiuso da {ctx.author}: {motivo}")
    except discord.Forbidden:
        await ctx.send(embed=error("Non ho i permessi per eliminare questo canale."))

# ── .addticket ────────────────────────────────────────────────────────────────
@bot.command(name="addticket")
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def addticket_cmd(ctx, membro: discord.Member):
    """Aggiunge un membro al ticket corrente.
    Utilizzo: .addticket @utente"""
    if not ctx.channel.name.startswith("ticket-"):
        return await ctx.send(embed=error("Questo comando può essere usato solo in un canale ticket."))
    await ctx.channel.set_permissions(membro, read_messages=True, send_messages=True)
    await ctx.send(embed=success(f"**{membro}** è stato aggiunto al ticket."))

# ── .removeticket ─────────────────────────────────────────────────────────────
@bot.command(name="removeticket")
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def removeticket_cmd(ctx, membro: discord.Member):
    """Rimuove un membro dal ticket corrente.
    Utilizzo: .removeticket @utente"""
    if not ctx.channel.name.startswith("ticket-"):
        return await ctx.send(embed=error("Questo comando può essere usato solo in un canale ticket."))
    if membro == ctx.author:
        return await ctx.send(embed=error("Non puoi rimuovere te stesso dal ticket."))
    await ctx.channel.set_permissions(membro, overwrite=None)
    await ctx.send(embed=success(f"**{membro}** è stato rimosso dal ticket."))

# ── Run ───────────────────────────────────────────────────────────────────────
if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN non impostato. Aggiungilo come segreto con il nome DISCORD_TOKEN."
    )

bot.run(TOKEN)
