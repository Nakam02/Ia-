import discord
from discord.ext import commands
from database import get_config, set_config, config_col

# ── Collection dédiée aux tickets ────────────────────────────────
from database import db
tickets_col = db["tickets"]

class WelcomeTickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ════════════════════════════════════════════════════════════════
    #  +join settings  — Configuration du message de bienvenue
    # ════════════════════════════════════════════════════════════════

    @commands.group(name="join", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def join_group(self, ctx):
        """Affiche la config bienvenue ou les sous-commandes disponibles"""
        cfg = await get_config(ctx.guild.id)
        ch_id  = cfg.get("welcome_channel_id")
        ch     = f"<#{ch_id}>" if ch_id else "Non configuré"
        msg    = cfg.get("welcome_message", "Bienvenue {mention} sur **{server}** !")
        img    = cfg.get("welcome_image_url", "Aucune")
        role_id = cfg.get("welcome_role_id")
        role   = f"<@&{role_id}>" if role_id else "Aucun"

        embed = discord.Embed(title="⚙️ Configuration Bienvenue", color=discord.Color.blurple())
        embed.add_field(name="📢 Salon",   value=ch,   inline=True)
        embed.add_field(name="🎭 Rôle",    value=role, inline=True)
        embed.add_field(name="💬 Message", value=msg,  inline=False)
        embed.add_field(name="🖼️ Image",   value=img,  inline=False)
        embed.set_footer(text="Variables : {mention} {name} {server} {count}")
        await ctx.send(embed=embed)

    @join_group.command(name="settings")
    @commands.has_permissions(administrator=True)
    async def join_settings(self, ctx):
        """Menu interactif de configuration de la bienvenue"""
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        embed = discord.Embed(
            title="🛠️ Configuration de la Bienvenue",
            description=(
                "Je vais te poser quelques questions.\n"
                "Réponds `skip` pour ignorer une étape.\n\n"
                "**Étape 1/4** — Mentionne le **salon** de bienvenue."
            ),
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

        updates = {}

        # — Salon —
        try:
            r = await self.bot.wait_for("message", check=check, timeout=60)
            if r.content.lower() != "skip":
                if r.channel_mentions:
                    updates["welcome_channel_id"] = r.channel_mentions[0].id
                else:
                    await ctx.send("❌ Salon invalide, étape ignorée.")
        except Exception:
            await ctx.send("❌ Temps écoulé."); return

        # — Rôle —
        await ctx.send("**Étape 2/4** — Mentionne le **rôle** à donner à l'arrivée (ou `skip`).")
        try:
            r = await self.bot.wait_for("message", check=check, timeout=60)
            if r.content.lower() != "skip":
                if r.role_mentions:
                    updates["welcome_role_id"] = r.role_mentions[0].id
                else:
                    await ctx.send("❌ Rôle invalide, étape ignorée.")
        except Exception:
            await ctx.send("❌ Temps écoulé."); return

        # — Message —
        await ctx.send(
            "**Étape 3/4** — Écris le **message** de bienvenue (ou `skip`).\n"
            "Variables : `{mention}` `{name}` `{server}` `{count}`"
        )
        try:
            r = await self.bot.wait_for("message", check=check, timeout=60)
            if r.content.lower() != "skip":
                updates["welcome_message"] = r.content
        except Exception:
            await ctx.send("❌ Temps écoulé."); return

        # — Image (URL ou pièce jointe) —
        await ctx.send(
            "**Étape 4/4** — Envoie une **image** (pièce jointe) ou une **URL d'image** pour la bannière "
            "de bienvenue (ou `skip`)."
        )
        try:
            r = await self.bot.wait_for("message", check=check, timeout=60)
            if r.content.lower() != "skip":
                if r.attachments:
                    updates["welcome_image_url"] = r.attachments[0].url
                elif r.content.startswith("http"):
                    updates["welcome_image_url"] = r.content.strip()
                else:
                    await ctx.send("❌ Format invalide, étape ignorée.")
        except Exception:
            await ctx.send("❌ Temps écoulé."); return

        if updates:
            await set_config(ctx.guild.id, updates)
            await ctx.send("✅ Configuration de bienvenue mise à jour !")
        else:
            await ctx.send("ℹ️ Aucune modification effectuée.")

    @join_group.command(name="test")
    @commands.has_permissions(administrator=True)
    async def join_test(self, ctx):
        """Simule un message de bienvenue pour tester la config"""
        await self._send_welcome(ctx.author)
        await ctx.send("✅ Message de bienvenue envoyé en test.")

    # ── Listener on_member_join ───────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cfg = await get_config(member.guild.id)

        # Rôle auto
        role_id = cfg.get("welcome_role_id")
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
                except Exception:
                    pass

        # Message de bienvenue
        await self._send_welcome(member)

    async def _send_welcome(self, member):
        cfg = await get_config(member.guild.id)
        ch_id = cfg.get("welcome_channel_id")
        if not ch_id:
            return
        channel = self.bot.get_channel(ch_id)
        if not channel:
            return

        template = cfg.get("welcome_message", "Bienvenue {mention} sur **{server}** !")
        text = template.format(
            mention=member.mention,
            name=member.display_name,
            server=member.guild.name,
            count=member.guild.member_count,
        )

        embed = discord.Embed(description=text, color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Membre #{member.guild.member_count}")

        image_url = cfg.get("welcome_image_url")
        if image_url:
            embed.set_image(url=image_url)

        await channel.send(embed=embed)

    # ════════════════════════════════════════════════════════════════
    #  +tickets  — Système de tickets avec support images
    # ════════════════════════════════════════════════════════════════

    @commands.group(name="tickets", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def tickets_group(self, ctx):
        """Affiche la config tickets ou les sous-commandes disponibles"""
        cfg = await get_config(ctx.guild.id)
        cat_id   = cfg.get("ticket_category_id")
        cat      = f"Catégorie ID `{cat_id}`" if cat_id else "Non configurée"
        log_id   = cfg.get("ticket_log_channel_id")
        log      = f"<#{log_id}>" if log_id else "Non configuré"
        sup_id   = cfg.get("ticket_support_role_id")
        sup      = f"<@&{sup_id}>" if sup_id else "Non configuré"
        msg_id   = cfg.get("ticket_panel_message_id")

        embed = discord.Embed(title="🎫 Configuration Tickets", color=discord.Color.gold())
        embed.add_field(name="📂 Catégorie",     value=cat, inline=True)
        embed.add_field(name="📋 Logs",          value=log, inline=True)
        embed.add_field(name="🛡️ Rôle support",  value=sup, inline=True)
        embed.add_field(name="📌 Panel",         value=f"Message ID `{msg_id}`" if msg_id else "Non envoyé", inline=False)
        await ctx.send(embed=embed)

    @tickets_group.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def tickets_setup(self, ctx):
        """Configure le système de tickets étape par étape"""
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("**Tickets — Étape 1/3** — Mentionne le **salon de logs** des tickets (ou `skip`).")
        updates = {}

        try:
            r = await self.bot.wait_for("message", check=check, timeout=60)
            if r.content.lower() != "skip" and r.channel_mentions:
                updates["ticket_log_channel_id"] = r.channel_mentions[0].id
        except Exception:
            await ctx.send("❌ Temps écoulé."); return

        await ctx.send("**Étape 2/3** — Mentionne le **rôle support** (accès aux tickets, ou `skip`).")
        try:
            r = await self.bot.wait_for("message", check=check, timeout=60)
            if r.content.lower() != "skip" and r.role_mentions:
                updates["ticket_support_role_id"] = r.role_mentions[0].id
        except Exception:
            await ctx.send("❌ Temps écoulé."); return

        await ctx.send(
            "**Étape 3/3** — Envoie une **image** (pièce jointe) ou une **URL** pour le panel "
            "de tickets (ou `skip`)."
        )
        try:
            r = await self.bot.wait_for("message", check=check, timeout=60)
            if r.content.lower() != "skip":
                if r.attachments:
                    updates["ticket_panel_image_url"] = r.attachments[0].url
                elif r.content.startswith("http"):
                    updates["ticket_panel_image_url"] = r.content.strip()
        except Exception:
            await ctx.send("❌ Temps écoulé."); return

        if updates:
            await set_config(ctx.guild.id, updates)
        await ctx.send("✅ Configuration tickets mise à jour ! Utilise `+tickets panel #salon` pour envoyer le panel.")

    @tickets_group.command(name="panel")
    @commands.has_permissions(administrator=True)
    async def tickets_panel(self, ctx, channel: discord.TextChannel = None):
        """Envoie le panel de création de tickets dans un salon"""
        channel = channel or ctx.channel
        cfg = await get_config(ctx.guild.id)

        embed = discord.Embed(
            title="🎫 Support — Créer un ticket",
            description=(
                "Tu as besoin d'aide ou tu as une question ?\n"
                "Clique sur le bouton ci-dessous pour ouvrir un ticket privé avec l'équipe."
            ),
            color=discord.Color.gold()
        )
        img = cfg.get("ticket_panel_image_url")
        if img:
            embed.set_image(url=img)
        embed.set_footer(text=ctx.guild.name)

        view = TicketCreateView(self.bot)
        msg = await channel.send(embed=embed, view=view)
        await set_config(ctx.guild.id, {"ticket_panel_message_id": msg.id, "ticket_panel_channel_id": channel.id})
        await ctx.send(f"✅ Panel envoyé dans {channel.mention}.")

    @tickets_group.command(name="close")
    async def tickets_close(self, ctx):
        """Ferme le ticket actuel (dans un salon de ticket)"""
        doc = await tickets_col.find_one({"channel_id": ctx.channel.id})
        if not doc:
            await ctx.send("❌ Ce salon n'est pas un ticket.")
            return
        await ctx.send("🔒 Fermeture du ticket dans 5 secondes...")
        import asyncio
        await asyncio.sleep(5)
        try:
            await ctx.channel.delete(reason=f"Ticket fermé par {ctx.author}")
        except Exception:
            pass
        await tickets_col.delete_one({"channel_id": ctx.channel.id})

        # Log
        cfg = await get_config(ctx.guild.id)
        log_id = cfg.get("ticket_log_channel_id")
        if log_id:
            log_ch = self.bot.get_channel(log_id)
            if log_ch:
                embed = discord.Embed(
                    title="🔒 Ticket fermé",
                    color=discord.Color.red()
                )
                embed.add_field(name="Fermé par", value=ctx.author.mention)
                embed.add_field(name="Ticket",    value=ctx.channel.name)
                await log_ch.send(embed=embed)

    @tickets_group.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def tickets_add(self, ctx, member: discord.Member):
        """Ajoute un membre au ticket actuel"""
        doc = await tickets_col.find_one({"channel_id": ctx.channel.id})
        if not doc:
            await ctx.send("❌ Ce salon n'est pas un ticket.")
            return
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
        await ctx.send(f"✅ {member.mention} a été ajouté au ticket.")

    @tickets_group.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def tickets_remove(self, ctx, member: discord.Member):
        """Retire un membre du ticket actuel"""
        doc = await tickets_col.find_one({"channel_id": ctx.channel.id})
        if not doc:
            await ctx.send("❌ Ce salon n'est pas un ticket.")
            return
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(f"✅ {member.mention} a été retiré du ticket.")


# ── Vue boutton de création de ticket ────────────────────────────

class TicketCreateView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📩 Créer un ticket", style=discord.ButtonStyle.primary, custom_id="ticket:create")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        cfg = await get_config(guild.id)

        # Vérifier si un ticket existe déjà
        existing = await tickets_col.find_one({"guild_id": guild.id, "user_id": member.id, "open": True})
        if existing:
            ch = guild.get_channel(existing["channel_id"])
            if ch:
                await interaction.response.send_message(
                    f"❌ Tu as déjà un ticket ouvert : {ch.mention}", ephemeral=True
                )
                return

        # Créer la catégorie/channel
        cat_id = cfg.get("ticket_category_id")
        category = guild.get_channel(cat_id) if cat_id else None
        sup_id = cfg.get("ticket_support_role_id")
        support_role = guild.get_role(sup_id) if sup_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_num = (await tickets_col.count_documents({"guild_id": guild.id})) + 1
        channel_name = f"ticket-{ticket_num:04d}-{member.name[:12].lower()}"

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket créé par {member}"
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur lors de la création : {e}", ephemeral=True)
            return

        await tickets_col.insert_one({
            "guild_id": guild.id,
            "user_id": member.id,
            "channel_id": channel.id,
            "open": True,
            "number": ticket_num,
        })

        # Message d'accueil dans le ticket (supporte image)
        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_num:04d}",
            description=(
                f"Bonjour {member.mention} !\n\n"
                "L'équipe va te répondre dès que possible.\n"
                "Tu peux envoyer des messages, images et fichiers ici.\n\n"
                "Utilise `+tickets close` pour fermer ce ticket."
            ),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        img = cfg.get("ticket_panel_image_url")
        if img:
            embed.set_image(url=img)

        close_view = TicketCloseView()
        ping = support_role.mention if support_role else ""
        await channel.send(content=ping, embed=embed, view=close_view)

        # Log
        log_id = cfg.get("ticket_log_channel_id")
        if log_id:
            log_ch = guild.get_channel(log_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="📩 Ticket ouvert",
                    color=discord.Color.green()
                )
                log_embed.add_field(name="Membre",  value=member.mention)
                log_embed.add_field(name="Salon",   value=channel.mention)
                log_embed.add_field(name="Numéro",  value=f"#{ticket_num:04d}")
                await log_ch.send(embed=log_embed)

        await interaction.response.send_message(
            f"✅ Ton ticket a été créé : {channel.mention}", ephemeral=True
        )


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        doc = await tickets_col.find_one({"channel_id": interaction.channel.id})
        if not doc:
            await interaction.response.send_message("❌ Ce salon n'est pas un ticket.", ephemeral=True)
            return
        await interaction.response.send_message("🔒 Fermeture dans 5 secondes...")
        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user}")
        except Exception:
            pass
        await tickets_col.delete_one({"channel_id": interaction.channel.id})


async def setup(bot):
    await bot.add_cog(WelcomeTickets(bot))
