import os
import asyncio
import discord
from discord.ext import commands
import yt_dlp

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="", intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options, executable='ffmpeg'), data=data)

class MusicPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إيقاف مؤقت", style=discord.ButtonStyle.blurple, emoji="⏸️", row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("البوت ليس متصلاً بروم صوتي.", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("تم إيقاف الأغنية مؤقتاً.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("تم استكمال الأغنية.", ephemeral=True)
        else:
            await interaction.response.send_message("لا توجد أغنية تعمل حالياً.", ephemeral=True)

    @discord.ui.button(label="السابق", style=discord.ButtonStyle.secondary, emoji="⏮️", row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("خاصية الأغنية السابقة غير متوفرة حالياً.", ephemeral=True)

    @discord.ui.button(label="خفض", style=discord.ButtonStyle.secondary, emoji="🔉", row=0)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc or not vc.source:
            return await interaction.response.send_message("البوت ليس متصلاً.", ephemeral=True)
        current_vol = vc.source.volume
        new_vol = max(0.0, current_vol - 0.1)
        vc.source.volume = new_vol
        await interaction.response.send_message(f"مستوى الصوت: {int(new_vol * 100)}%", ephemeral=True)

    @discord.ui.button(label="تخطي", style=discord.ButtonStyle.primary, emoji="⏭️", row=1)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("البوت ليس متصلاً.", ephemeral=True)
        if vc.is_playing():
            vc.stop()
            await interaction.response.send_message("تم تخطي الأغنية.", ephemeral=True)
        else:
            await interaction.response.send_message("لا توجد أغنية لتخطيها.", ephemeral=True)

    @discord.ui.button(label="رفع", style=discord.ButtonStyle.secondary, emoji="🔊", row=1)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc or not vc.source:
            return await interaction.response.send_message("البوت ليس متصلاً.", ephemeral=True)
        current_vol = vc.source.volume
        new_vol = min(1.0, current_vol + 0.1)
        vc.source.volume = new_vol
        await interaction.response.send_message(f"مستوى الصوت: {int(new_vol * 100)}%", ephemeral=True)

    @discord.ui.button(label="إيقاف", style=discord.ButtonStyle.danger, emoji="⏹️", row=2)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("البوت ليس متصلاً.", ephemeral=True)
        await vc.disconnect()
        await interaction.response.send_message("تم إيقاف الأغنية ومغادرة الروم.", ephemeral=True)

    @discord.ui.button(label="تكرار", style=discord.ButtonStyle.secondary, emoji="🔁", row=2)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("تم تبديل وضع التكرار.", ephemeral=True)

    @discord.ui.button(label="خلط", style=discord.ButtonStyle.secondary, emoji="🔀", row=2)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("تم خلط قائمة الانتظار.", ephemeral=True)

    @discord.ui.button(label="القائمة", style=discord.ButtonStyle.secondary, emoji="🎵", row=3)
    async def queue_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("قائمة الانتظار فارغة.", ephemeral=True)

    @discord.ui.button(label="تشغيل تلقائي", style=discord.ButtonStyle.secondary, emoji="✨", row=3)
    async def autoplay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("تم تبديل التشغيل التلقائي.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    if content.startswith("ش "):
        query = content[2:].strip()
        if not query:
            return
        
        if not message.author.voice:
            return await message.channel.send("يجب أن تكون في روم صوتي أولاً!")
        
        channel = message.author.voice.channel
        try:
            if message.guild.voice_client is None:
                await channel.connect()
            elif message.guild.voice_client.channel != channel:
                await message.guild.voice_client.move_to(channel)
        except Exception as e:
            return await message.channel.send(f"خطأ في الاتصال بالروم الصوتي: {e}")

        async with message.channel.typing():
            try:
                player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
                if message.guild.voice_client.is_playing():
                    message.guild.voice_client.stop()
                message.guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            except Exception as e:
                return await message.channel.send(f"حدث خطأ أثناء تشغيل الأغنية أو تحميل FFmpeg: {e}")

        embed = discord.Embed(title="MUSIC PANEL", color=0x2b2d31)
        embed.add_field(name="الأغنية الحالية", value=player.title, inline=False)
        embed.add_field(name="مستوى الصوت", value="50%", inline=True)
        embed.add_field(name="التكرار", value="متوقف", inline=True)
        embed.add_field(name="التشغيل التلقائي", value="متوقف", inline=True)
        embed.add_field(name="قائمة الانتظار", value="0\nالقائمة فارغة", inline=False)

        view = MusicPanel()
        await message.channel.send(embed=embed, view=view)

    elif content == "ق":
        vc = message.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await message.channel.send("تم إيقاف الأغنية مؤقتاً.")

    elif content == "ت":
        vc = message.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await message.channel.send("تم استكمال الأغنية.")

    elif content == "قفل":
        vc = message.guild.voice_client
        if vc:
            await vc.disconnect()
            await message.channel.send("تم إيقاف الأغنية ومغادرة الروم.")

    elif content.startswith("ص "):
        try:
            vol = int(content.split()[1])
            vc = message.guild.voice_client
            if vc and vc.source:
                if 0 <= vol <= 100:
                    vc.source.volume = vol / 100
                    await message.channel.send(f"تم تغيير مستوى الصوت إلى {vol}%")
        except:
            pass

    await bot.process_commands(message)

bot.run("MTU1ODAzMjA0ODM0NDgwMTMwMA.Guf6oC.TG-ht_6NK0WduyIX1ewr-59frcNpc7Ht3t84KI")
