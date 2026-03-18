import discord
from discord.ext import commands
from database import blacklist_col, owners_col, get_config, set_config

class ControleBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owners = set()  # owners en RAM (chargés au démarrage)

    async def cog_load(self):
        """Charge les owners depuis MongoDB au démarrage"""
        doc = await owners_col.find_one({"_id": "owners"})
        if doc:
            self.owners = set(doc.get("ids", []))

    @commands.command(name="setname")
    @commands.is_owner()
    async def set_name(self, ctx, *, name: str):
        """Change le nom du bot"""
        await ctx.bot.user.edit(username=name)
        await ctx.send(f"✅ Nom changé en **{name}**.")

    @commands.command()
    @commands.is_owner()
    async def say(self, ctx, *, message: str):
        """Fait dire un message au bot"""
        await ctx.message.delete()
        await ctx.send(message)

    @commands.command()
    @commands.is_owner()
    async def owner(self, ctx, member: discord.Member = None):
        """Donne/affiche le grade Owner"""
        if member:
            self.owners.add(member.id)
            await owners_col.update_one(
                {"_id": "owners"},
                {"$addToSet": {"ids": member.id}},
                upsert=True
            )
            await ctx.send(f"✅ {member.mention} est maintenant Owner du bot.")
        else:
            desc = "\n".join([f"<@{uid}>" for uid in self.owners]) or "Aucun owner."
            embed = discord.Embed(title="👑 Owners du bot", description=desc, color=discord.Color.gold())
            await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def unowner(self, ctx, member: discord.Member):
        """Retire le grade Owner"""
        self.owners.discard(member.id)
        await owners_col.update_one(
            {"_id": "owners"},
            {"$pull": {"ids": member.id}}
        )
        await ctx.send(f"✅ {member.mention} n'est plus Owner.")

    @commands.command()
    @commands.is_owner()
    async def bl(self, ctx, member: discord.Member = None, *, reason: str = "Aucune raison"):
        """Blacklist globale : ajoute ou affiche"""
        if member:
            await blacklist_col.update_one(
                {"user_id": member.id},
                {"$set": {"user_id": member.id, "reason": reason}},
                upsert=True
            )
            await ctx.send(f"✅ {member.mention} ajouté à la blacklist. Raison : {reason}")
        else:
            docs = blacklist_col.find({})
            lines = []
            async for doc in docs:
                lines.append(f"<@{doc['user_id']}> - {doc.get('reason', '?')}")
            desc = "\n".join(lines) or "Blacklist vide."
            embed = discord.Embed(title="🚫 Blacklist", description=desc, color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def unbl(self, ctx, member: discord.Member):
        """Retire de la blacklist"""
        await blacklist_col.delete_one({"user_id": member.id})
        await ctx.send(f"✅ {member.mention} retiré de la blacklist.")

    @commands.command()
    @commands.is_owner()
    async def blinfo(self, ctx, member: discord.Member):
        """Infos blacklist d'un membre"""
        doc = await blacklist_col.find_one({"user_id": member.id})
        if not doc:
            await ctx.send(f"✅ {member.mention} n'est pas dans la blacklist.")
            return
        embed = discord.Embed(title=f"🚫 Blacklist - {member}", color=discord.Color.red())
        embed.add_field(name="Raison", value=doc.get("reason", "?"))
        await ctx.send(embed=embed)

    @commands.command(name="clearbl")
    @commands.is_owner()
    async def clear_bl(self, ctx):
        """Vide toute la blacklist"""
        await blacklist_col.delete_many({})
        await ctx.send("✅ Blacklist vidée.")

    @commands.command()
    @commands.is_owner()
    async def prefix(self, ctx, new_prefix: str):
        """Change le préfixe du bot sur ce serveur"""
        await set_config(ctx.guild.id, {"prefix": new_prefix})
        ctx.bot.command_prefix = new_prefix
        await ctx.send(f"✅ Préfixe changé en `{new_prefix}`.")

    @commands.command(name="serverlist")
    @commands.is_owner()
    async def server_list(self, ctx):
        """Liste des serveurs du bot"""
        desc = "\n".join([f"• **{g.name}** (ID: `{g.id}`) - {g.member_count} membres" for g in ctx.bot.guilds])
        embed = discord.Embed(title=f"🌐 Serveurs ({len(ctx.bot.guilds)})", description=desc, color=discord.Color.blurple())
        await ctx.send(embed=embed)

    @commands.command(name="setpic")
    @commands.is_owner()
    async def set_pic(self, ctx):
        """Change l'avatar du bot (envoie une image en pièce jointe ou une URL)"""
        # Priorité à la pièce jointe
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if not attachment.content_type or not attachment.content_type.startswith("image/"):
                await ctx.send("❌ Le fichier joint n'est pas une image.")
                return
            image_data = await attachment.read()
            await ctx.bot.user.edit(avatar=image_data)
            await ctx.send("✅ Avatar du bot mis à jour !")
            return

        # Sinon cherche une URL dans le contenu
        content = ctx.message.content
        # Extrait l'URL après la commande
        parts = content.split(maxsplit=1)
        url = parts[1].strip() if len(parts) > 1 else None

        if not url or not url.startswith("http"):
            await ctx.send(
                "❌ Envoie une image en pièce jointe ou fournis une URL.\n"
                "Exemples :\n"
                "• `+setpic` avec une image attachée\n"
                "• `+setpic https://example.com/image.png`"
            )
            return

        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await ctx.send(f"❌ Impossible de télécharger l'image (HTTP {resp.status}).")
                        return
                    content_type = resp.headers.get("Content-Type", "")
                    if not content_type.startswith("image/"):
                        await ctx.send("❌ L'URL ne pointe pas vers une image valide.")
                        return
                    image_data = await resp.read()
            await ctx.bot.user.edit(avatar=image_data)
            await ctx.send("✅ Avatar du bot mis à jour !")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la mise à jour de l'avatar : {e}")

    # ── Vérification blacklist à chaque commande ──────────────────
    @commands.Cog.listener()
    async def on_command(self, ctx):
        doc = await blacklist_col.find_one({"user_id": ctx.author.id})
        if doc:
            try:
                await ctx.send("🚫 Tu es dans la blacklist du bot et ne peux pas utiliser ses commandes.")
            except Exception:
                pass
            ctx.command.reset_cooldown(ctx)
            raise commands.CheckFailure("Blacklisted")

async def setup(bot):
    await bot.add_cog(ControleBot(bot))
