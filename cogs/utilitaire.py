import discord
from discord.ext import commands
import wikipedia
import asyncio
import ast
import operator
import re

wikipedia.set_lang("fr")
sniped_messages = {}

def _truncate(text, limit=4000):
    return text[:limit] + "\n*(liste tronquee)*" if len(text) > limit else text

class Utilitaire(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.author.bot and message.guild:
            sniped_messages[message.channel.id] = message

    @commands.command()
    async def changelogs(self, ctx):
        embed = discord.Embed(title="Changelogs", description="Aucune mise a jour recente.", color=discord.Color.blurple())
        await ctx.send(embed=embed)

    @commands.command()
    async def allbots(self, ctx):
        bots = [m for m in ctx.guild.members if m.bot]
        desc = _truncate("\n".join([f"- {b.mention}" for b in bots]) or "Aucun bot trouve.")
        embed = discord.Embed(title=f"Bots ({len(bots)})", description=desc, color=discord.Color.blurple())
        await ctx.send(embed=embed)

    @commands.command()
    async def alladmins(self, ctx):
        admins = [m for m in ctx.guild.members if not m.bot and m.guild_permissions.administrator]
        desc = _truncate("\n".join([f"- {a.mention}" for a in admins]) or "Aucun admin trouve.")
        embed = discord.Embed(title=f"Admins ({len(admins)})", description=desc, color=discord.Color.gold())
        await ctx.send(embed=embed)

    @commands.command()
    async def botadmins(self, ctx):
        bots = [m for m in ctx.guild.members if m.bot and m.guild_permissions.administrator]
        desc = _truncate("\n".join([f"- {b.mention}" for b in bots]) or "Aucun bot admin trouve.")
        embed = discord.Embed(title=f"Bots Admins ({len(bots)})", description=desc, color=discord.Color.orange())
        await ctx.send(embed=embed)

    @commands.command()
    async def boosters(self, ctx):
        boosters = ctx.guild.premium_subscribers
        desc = _truncate("\n".join([f"- {b.mention}" for b in boosters]) or "Aucun booster.")
        embed = discord.Embed(title=f"Boosters ({len(boosters)})", description=desc, color=discord.Color.from_rgb(255, 182, 193))
        await ctx.send(embed=embed)

    @commands.command()
    async def rolemembers(self, ctx, *, role: discord.Role):
        members = role.members
        desc = _truncate("\n".join([f"- {m.mention}" for m in members]) or "Aucun membre.")
        embed = discord.Embed(title=f"Membres avec {role.name} ({len(members)})", description=desc, color=role.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def serverinfo(self, ctx):
        g = ctx.guild
        embed = discord.Embed(title=f"Info : {g.name}", color=discord.Color.blurple())
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Membres", value=g.member_count)
        embed.add_field(name="Salons", value=len(g.channels))
        embed.add_field(name="Roles", value=len(g.roles))
        embed.add_field(name="Boosts", value=g.premium_subscription_count)
        embed.add_field(name="Proprietaire", value=g.owner.mention)
        embed.add_field(name="Cree le", value=g.created_at.strftime("%d/%m/%Y"))
        await ctx.send(embed=embed)

    @commands.command()
    async def vocinfo(self, ctx):
        channels = ctx.guild.voice_channels
        total = sum(len(c.members) for c in channels)
        desc = _truncate("\n".join([f"- **{c.name}** : {len(c.members)} membre(s)" for c in channels if c.members]))
        embed = discord.Embed(title="Activite vocale", description=desc or "Aucun membre en vocal.", color=discord.Color.blurple())
        embed.set_footer(text=f"Total en vocal : {total}")
        await ctx.send(embed=embed)

    @commands.command()
    async def role(self, ctx, *, role: discord.Role):
        embed = discord.Embed(title=f"Role : {role.name}", color=role.color)
        embed.add_field(name="ID", value=role.id)
        embed.add_field(name="Membres", value=len(role.members))
        embed.add_field(name="Mentionnable", value=role.mentionable)
        embed.add_field(name="Hisse", value=role.hoist)
        embed.add_field(name="Cree le", value=role.created_at.strftime("%d/%m/%Y"))
        await ctx.send(embed=embed)

    @commands.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        embed = discord.Embed(title=f"Salon : #{channel.name}", color=discord.Color.blurple())
        embed.add_field(name="ID", value=channel.id)
        embed.add_field(name="Categorie", value=str(channel.category) or "Aucune")
        embed.add_field(name="NSFW", value=channel.is_nsfw())
        embed.add_field(name="Slowmode", value=f"{channel.slowmode_delay}s")
        embed.add_field(name="Cree le", value=channel.created_at.strftime("%d/%m/%Y"))
        await ctx.send(embed=embed)

    @commands.command()
    async def user(self, ctx, member: discord.User = None):
        member = member or ctx.author
        embed = discord.Embed(title=str(member), color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Bot", value=member.bot)
        embed.add_field(name="Cree le", value=member.created_at.strftime("%d/%m/%Y"))
        await ctx.send(embed=embed)

    @commands.command()
    async def member(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=member.display_name, color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Surnom", value=member.nick or "Aucun")
        embed.add_field(name="A rejoint le", value=member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "?")
        roles_str = _truncate(", ".join([r.name for r in member.roles[1:]]) or "Aucun", 1024)
        embed.add_field(name="Roles", value=roles_str)
        await ctx.send(embed=embed)

    @commands.command()
    async def pic(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"Photo de {member.display_name}", color=discord.Color.blurple())
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def banner(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user = await ctx.bot.fetch_user(member.id)
        if user.banner:
            embed = discord.Embed(title=f"Banniere de {member.display_name}", color=discord.Color.blurple())
            embed.set_image(url=user.banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{member.display_name} n'a pas de banniere.")

    @commands.command(name="serverpic")
    async def server_pic(self, ctx):
        if ctx.guild.icon:
            embed = discord.Embed(title=f"Icone de {ctx.guild.name}", color=discord.Color.blurple())
            embed.set_image(url=ctx.guild.icon.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Ce serveur n'a pas d'icone.")

    @commands.command(name="serverbanner")
    async def server_banner(self, ctx):
        if ctx.guild.banner:
            embed = discord.Embed(title=f"Banniere de {ctx.guild.name}", color=discord.Color.blurple())
            embed.set_image(url=ctx.guild.banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Ce serveur n'a pas de banniere.")

    @commands.command()
    async def snipe(self, ctx):
        msg = sniped_messages.get(ctx.channel.id)
        if not msg:
            await ctx.send("Aucun message supprime recemment dans ce salon. (Le snipe se remet a zero au redemarrage du bot)")
            return
        embed = discord.Embed(
            description=msg.content[:4096] if msg.content else "*[pas de texte]*",
            color=discord.Color.red(),
            timestamp=msg.created_at
        )
        embed.set_author(name=str(msg.author), icon_url=msg.author.display_avatar.url)
        embed.set_footer(text=f"Supprime dans #{ctx.channel.name}")
        if msg.attachments:
            embed.set_image(url=msg.attachments[0].proxy_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def emoji(self, ctx, *, emoji_input: str):
        """Affiche un emoji custom — fonctionne avec n'importe quel serveur.

        Usages :
          +emoji <:nom:ID>          — mention directe (tout serveur)
          +emoji <a:nom:ID>         — mention animée (tout serveur)
          +emoji nom                — cherche dans le serveur actuel
          +emoji copy <:nom:ID>     — copie l'emoji dans ce serveur (Admin)
        """
        # ── Mode copy ───────────────────────────────────────────────
        copy_mode = False
        if emoji_input.lower().startswith("copy "):
            copy_mode = True
            emoji_input = emoji_input[5:].strip()

        # ── Résolution de l'emoji ────────────────────────────────────
        emoji_id    = None
        emoji_name  = None
        is_animated = False
        emoji_url   = None

        # Cas 1 : mention <:nom:ID> ou <a:nom:ID>
        match = re.match(r"<(a?):(\w+):(\d+)>", emoji_input)
        if match:
            is_animated = match.group(1) == "a"
            emoji_name  = match.group(2)
            emoji_id    = int(match.group(3))
            ext         = "gif" if is_animated else "png"
            emoji_url   = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=128"

        # Cas 2 : ID brut (nombre)
        elif emoji_input.strip().isdigit():
            emoji_id   = int(emoji_input.strip())
            emoji_url  = f"https://cdn.discordapp.com/emojis/{emoji_id}.png?size=128"
            emoji_name = f"emoji_{emoji_id}"

        # Cas 3 : nom — cherche dans le serveur actuel
        else:
            name = emoji_input.strip(":")
            local = discord.utils.get(ctx.guild.emojis, name=name)
            if local:
                emoji_id    = local.id
                emoji_name  = local.name
                is_animated = local.animated
                ext         = "gif" if is_animated else "png"
                emoji_url   = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=128"
            else:
                await ctx.send(
                    f"❌ Emoji `{name}` introuvable sur ce serveur.\n"
                    "Astuce : utilise la mention directe `<:nom:ID>` pour cibler n'importe quel emoji."
                )
                return

        if not emoji_url:
            await ctx.send("❌ Format d'emoji invalide.")
            return

        # ── Mode affichage ────────────────────────────────────────────
        if not copy_mode:
            embed = discord.Embed(
                title=f"{'🎞️' if is_animated else '😀'} Emoji : {emoji_name}",
                color=discord.Color.blurple()
            )
            embed.set_image(url=emoji_url)
            if emoji_id:
                embed.set_footer(text=f"ID : {emoji_id} • {'Animé' if is_animated else 'Statique'}")
            if ctx.author.guild_permissions.manage_emojis:
                embed.description = "💡 Utilise `+emoji copy <:nom:ID>` pour copier cet emoji dans ce serveur."
            await ctx.send(embed=embed)
            return

        # ── Mode copy ─────────────────────────────────────────────────
        if not ctx.author.guild_permissions.manage_emojis:
            await ctx.send("❌ Tu as besoin de la permission **Gérer les emojis** pour copier un emoji.")
            return
        if not ctx.guild.me.guild_permissions.manage_emojis:
            await ctx.send("❌ Le bot n'a pas la permission **Gérer les emojis** sur ce serveur.")
            return

        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji_url) as resp:
                    if resp.status != 200:
                        emoji_url_gif = emoji_url.replace(".png", ".gif")
                        async with session.get(emoji_url_gif) as resp2:
                            if resp2.status != 200:
                                await ctx.send(f"❌ Impossible de télécharger l'emoji (HTTP {resp.status}).")
                                return
                            image_data = await resp2.read()
                            is_animated = True
                    else:
                        image_data = await resp.read()

            new_emoji = await ctx.guild.create_custom_emoji(
                name=emoji_name,
                image=image_data,
                reason=f"Copié par {ctx.author} via +emoji copy"
            )
            embed = discord.Embed(
                title="✅ Emoji copié !",
                description=f"{new_emoji} **{new_emoji.name}** a été ajouté à ce serveur.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=new_emoji.url)
            await ctx.send(embed=embed)

        except discord.HTTPException as e:
            if e.code == 30008:
                await ctx.send("❌ Ce serveur a atteint la limite maximale d'emojis.")
            else:
                await ctx.send(f"❌ Erreur Discord lors de la copie : {e}")
        except Exception as e:
            await ctx.send(f"❌ Erreur inattendue : {e}")

    @commands.command()
    async def image(self, ctx, *, query: str):
        await ctx.send(f"Recherche d'images pour : **{query}**\n*(Integre une API image comme SerpAPI pour activer cette commande)*")

    @commands.command()
    async def suggestion(self, ctx, *, message: str):
        embed = discord.Embed(title="Nouvelle suggestion", description=message[:4096], color=discord.Color.green())
        embed.set_footer(text=f"Par {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

    @commands.command()
    async def wiki(self, ctx, *, query: str):
        try:
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(None, lambda: wikipedia.summary(query, sentences=3))
            page = await loop.run_in_executor(None, lambda: wikipedia.page(query))
            embed = discord.Embed(title=page.title[:256], description=summary[:4096], url=page.url, color=discord.Color.blurple())
            await ctx.send(embed=embed)
        except wikipedia.exceptions.DisambiguationError as e:
            await ctx.send(f"Terme ambigu. Precise parmi : {', '.join(e.options[:5])}")
        except wikipedia.exceptions.PageError:
            await ctx.send(f"Aucun resultat Wikipedia pour **{query}**.")
        except Exception as e:
            await ctx.send(f"Erreur Wikipedia : {e}")

    @commands.command(name="search")
    async def search_wiki(self, ctx, source: str, *, query: str):
        if source.lower() != "wiki":
            await ctx.send("Usage : +search wiki <mot-cle>")
            return
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, lambda: wikipedia.search(query))
            desc = _truncate("\n".join([f"- {r}" for r in results]) or "Aucun resultat.")
            embed = discord.Embed(title=f"Resultats pour : {query}", description=desc, color=discord.Color.blurple())
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Erreur : {e}")

    @commands.command()
    async def calc(self, ctx, *, expression: str):
        ops = {
            ast.Add: operator.add, ast.Sub: operator.sub,
            ast.Mult: operator.mul, ast.Div: operator.truediv,
            ast.Pow: operator.pow, ast.USub: operator.neg,
            ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
        }
        def safe_eval(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            elif isinstance(node, ast.BinOp) and type(node.op) in ops:
                return ops[type(node.op)](safe_eval(node.left), safe_eval(node.right))
            elif isinstance(node, ast.UnaryOp) and type(node.op) in ops:
                return ops[type(node.op)](safe_eval(node.operand))
            else:
                raise ValueError("Expression non supportee")
        try:
            tree = ast.parse(expression, mode="eval")
            result = safe_eval(tree.body)
            if isinstance(result, float) and result == int(result):
                result = int(result)
            await ctx.send(f"`{expression}` = **{result}**")
        except ZeroDivisionError:
            await ctx.send("Division par zero impossible.")
        except Exception:
            await ctx.send("Expression invalide. Exemple : +calc 2+2")

    @commands.command()
    async def invite(self, ctx):
        perms = discord.Permissions(
            administrator=True
        )
        url = discord.utils.oauth_url(ctx.bot.user.id, permissions=perms)
        embed = discord.Embed(
            title="Inviter le bot",
            description=f"[Clique ici pour inviter le bot sur ton serveur]({url})",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)
        embed.set_footer(text="Necessite les permissions Administrateur")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utilitaire(bot))
