import discord
from discord.ext import commands
import asyncio
import random

class GestionServeur(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def giveaway(self, ctx):
        """Menu interactif pour créer un giveaway"""
        await ctx.send("🎉 **Création d'un giveaway** - Quel est le prix à gagner ?")
        def check(m): return m.author == ctx.author and m.channel == ctx.channel
        try:
            prize_msg = await self.bot.wait_for("message", check=check, timeout=30)
            prize = prize_msg.content
            await ctx.send("⏱️ Durée du giveaway (ex: `1h`, `30m`, `1j`) ?")
            dur_msg = await self.bot.wait_for("message", check=check, timeout=30)
            duree = dur_msg.content
            multiplicateurs = {"s": 1, "m": 60, "h": 3600, "j": 86400}
            try:
                temps = int(duree[:-1]) * multiplicateurs.get(duree[-1], 1)
            except Exception:
                await ctx.send("❌ Format de durée invalide. Exemple : `10m`, `2h`, `1j`")
                return
            embed = discord.Embed(
                title="🎉 GIVEAWAY !",
                description=f"**Prix :** {prize}\n**Durée :** {duree}\nRéagis avec 🎉 pour participer !",
                color=discord.Color.gold()
            )
            gaw_msg = await ctx.send(embed=embed)
            await gaw_msg.add_reaction("🎉")

            async def end_giveaway():
                await asyncio.sleep(temps)
                try:
                    gaw_msg_updated = await ctx.channel.fetch_message(gaw_msg.id)
                    reaction = discord.utils.get(gaw_msg_updated.reactions, emoji="🎉")
                    if reaction:
                        users = [u async for u in reaction.users() if not u.bot]
                        if users:
                            winner = random.choice(users)
                            await ctx.send(f"🎊 Félicitations {winner.mention} ! Tu as gagné **{prize}** !")
                        else:
                            await ctx.send("❌ Aucun participant au giveaway.")
                    else:
                        await ctx.send("❌ Aucune réaction trouvée.")
                except Exception as e:
                    await ctx.send(f"❌ Erreur lors de la fin du giveaway : {e}")
            asyncio.create_task(end_giveaway())
            await ctx.send(f"✅ Giveaway lancé ! Fin dans **{duree}**.")
        except asyncio.TimeoutError:
            await ctx.send("❌ Temps écoulé, giveaway annulé.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, duree: int, channel: discord.TextChannel = None):
        """Change le slowmode d'un salon (en secondes, max 21600)"""
        channel = channel or ctx.channel
        duree = min(duree, 21600)
        await channel.edit(slowmode_delay=duree)
        await ctx.send(f"⏱️ Slowmode de {channel.mention} réglé à **{duree}s**.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def renew(self, ctx, channel: discord.TextChannel = None):
        """Supprime et recrée un salon textuel"""
        channel = channel or ctx.channel
        pos = channel.position
        new_channel = await channel.clone(reason=f"Renew par {ctx.author}")
        await channel.delete()
        await new_channel.edit(position=pos)
        await new_channel.send(f"✅ Salon recréé par {ctx.author.mention}.")

    @commands.command()
    @commands.has_permissions(move_members=True)
    async def voicemove(self, ctx, source: discord.VoiceChannel = None, dest: discord.VoiceChannel = None):
        """Déplace tous les membres d'un vocal vers un autre"""
        if not source or not dest:
            await ctx.send("Usage : `+voicemove #source #destination`")
            return
        count = 0
        for m in source.members:
            await m.move_to(dest)
            count += 1
        await ctx.send(f"✅ {count} membre(s) déplacé(s) vers {dest.mention}.")

    @commands.command()
    @commands.has_permissions(move_members=True)
    async def voicekick(self, ctx, member: discord.Member):
        """Déconnecte un membre du vocal"""
        if member.voice:
            await member.move_to(None)
            await ctx.send(f"✅ {member.mention} a été déconnecté du vocal.")
        else:
            await ctx.send(f"❌ {member.mention} n'est pas en vocal.")

    @commands.command()
    @commands.has_permissions(move_members=True)
    async def bringall(self, ctx, channel: discord.VoiceChannel):
        """Amène tous les membres en vocal vers un salon"""
        count = 0
        for vc in ctx.guild.voice_channels:
            for m in vc.members:
                if vc != channel:
                    await m.move_to(channel)
                    count += 1
        await ctx.send(f"✅ {count} membre(s) déplacé(s) vers {channel.mention}.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def massiverole(self, ctx, role: discord.Role, filter_role: discord.Role = None):
        """Ajoute un rôle à tous les membres"""
        members = filter_role.members if filter_role else ctx.guild.members
        count = 0
        for m in members:
            if role not in m.roles:
                await m.add_roles(role)
                count += 1
        await ctx.send(f"✅ Rôle **{role.name}** ajouté à {count} membre(s).")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmassiverole(self, ctx, role: discord.Role, filter_role: discord.Role = None):
        """Retire un rôle à tous les membres"""
        members = filter_role.members if filter_role else ctx.guild.members
        count = 0
        for m in members:
            if role in m.roles:
                await m.remove_roles(role)
                count += 1
        await ctx.send(f"✅ Rôle **{role.name}** retiré à {count} membre(s).")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx, channel: discord.TextChannel = None, *, args: str = None):
        """Crée un embed personnalisé de manière interactive ou en une ligne.

        Usage interactif : +embed
        Usage rapide     : +embed #salon Titre | Description | #couleur | url_image
        """
        channel = channel or ctx.channel

        # ── Mode interactif ──────────────────────────────────────
        if not args:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            questions = [
                ("titre",       "📝 **Titre** de l'embed (ou `skip`) :"),
                ("description", "📄 **Description** (ou `skip`) :"),
                ("couleur",     "🎨 **Couleur** hex (ex: `#ff0000`) (ou `skip`) :"),
                ("image",       "🖼️ **Image** — envoie une pièce jointe ou une URL (ou `skip`) :"),
                ("thumbnail",   "🔍 **Miniature** (URL ou pièce jointe) (ou `skip`) :"),
                ("footer",      "🔖 **Footer** (ou `skip`) :"),
                ("salon",       f"📢 **Salon de destination** (mention) (ou `skip` pour {channel.mention}) :"),
            ]

            data = {}
            for key, question in questions:
                await ctx.send(question)
                try:
                    r = await self.bot.wait_for("message", check=check, timeout=60)
                    if r.content.lower() == "skip":
                        continue
                    if key in ("image", "thumbnail"):
                        if r.attachments:
                            data[key] = r.attachments[0].url
                        elif r.content.startswith("http"):
                            data[key] = r.content.strip()
                    elif key == "salon":
                        if r.channel_mentions:
                            channel = r.channel_mentions[0]
                    else:
                        data[key] = r.content
                except Exception:
                    await ctx.send("❌ Temps écoulé.")
                    return

            if not data.get("titre") and not data.get("description"):
                await ctx.send("❌ Un titre ou une description est requis.")
                return

            color = discord.Color.blurple()
            if data.get("couleur"):
                try:
                    color = discord.Color(int(data["couleur"].lstrip("#"), 16))
                except Exception:
                    pass

            embed = discord.Embed(
                title=data.get("titre", discord.Embed.Empty),
                description=data.get("description", discord.Embed.Empty),
                color=color
            )
            if data.get("image"):
                embed.set_image(url=data["image"])
            if data.get("thumbnail"):
                embed.set_thumbnail(url=data["thumbnail"])
            if data.get("footer"):
                embed.set_footer(text=data["footer"])

            await channel.send(embed=embed)
            if channel != ctx.channel:
                await ctx.send(f"✅ Embed envoyé dans {channel.mention}.")

        # ── Mode rapide : +embed #salon Titre | Description | #couleur | url_image ──
        else:
            parts = [p.strip() for p in args.split("|")]
            titre       = parts[0] if len(parts) > 0 else None
            description = parts[1] if len(parts) > 1 else None
            couleur_str = parts[2] if len(parts) > 2 else None
            image_url   = parts[3] if len(parts) > 3 else None

            color = discord.Color.blurple()
            if couleur_str:
                try:
                    color = discord.Color(int(couleur_str.lstrip("#"), 16))
                except Exception:
                    pass

            if not titre and not description:
                await ctx.send(
                    "❌ Usage : `+embed [#salon] Titre | Description | #couleur | url_image`\n"
                    "Ou utilise `+embed` seul pour le mode interactif."
                )
                return

            embed = discord.Embed(
                title=titre or discord.Embed.Empty,
                description=description or discord.Embed.Empty,
                color=color
            )
            if image_url and image_url.startswith("http"):
                embed.set_image(url=image_url)

            # Vérifie si une image est attachée au message
            if ctx.message.attachments:
                embed.set_image(url=ctx.message.attachments[0].url)

            await channel.send(embed=embed)
            if channel != ctx.channel:
                await ctx.send(f"✅ Embed envoyé dans {channel.mention}.")


async def setup(bot):
    await bot.add_cog(GestionServeur(bot))
