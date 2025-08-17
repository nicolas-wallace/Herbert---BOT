import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import yt_dlp
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Configurações do yt_dlp
ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'source_address': '0.0.0.0'
}

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -analyzeduration 0 -loglevel 0',
    'options': '-vn -af "volume=0.5"'
}

async def get_info(url):
    """Extrai info do YouTube sem travar o bot"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False))

@bot.event
async def on_voice_state_update(member, before, after):
    # Apenas logando desconexões do bot
    if member.id == bot.user.id and after.channel is None:
        print(f"Bot desconectado do canal {before.channel}")

@bot.command()
async def play(ctx, url: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Você precisa estar em um canal de voz para usar este comando!")
        return

    channel = ctx.author.voice.channel
    voice_client = ctx.guild.voice_client

    try:
        # Conecta no canal se não estiver conectado
        if not voice_client:
            voice_client = await channel.connect(timeout=30)
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        info = await get_info(url)
        if not info:
            await ctx.send("Não foi possível extrair informações do vídeo.")
            return

        # Se for playlist, pega o primeiro vídeo válido
        if 'entries' in info and len(info['entries']) > 0:
            for entry in info['entries']:
                if entry:  # Ignora vídeos inválidos
                    info = entry
                    break

        # Pega a melhor URL de áudio
        stream_url = None
        if 'url' in info:
            stream_url = info['url']
        elif 'formats' in info:
            stream_url = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), None)

        if not stream_url:
            await ctx.send("Não foi possível extrair a URL de áudio.")
            return

        source = discord.FFmpegPCMAudio(
            stream_url,
            before_options=ffmpeg_opts['before_options'],
            options=ffmpeg_opts['options']
        )

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(source)
        await ctx.send(f"Tocando: {info.get('title', 'Desconhecido')}")

    except Exception as e:
        await ctx.send(f"Ocorreu um erro: {e}")

@bot.command()
async def leave(ctx):
    """Desconecta o bot do canal de voz"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Desconectado do canal de voz!")

@bot.command()
async def pause(ctx):
    """Pausa a música atual"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Música pausada!")

@bot.command()
async def resume(ctx):
    """Continua a música pausada"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Música continuando!")

@bot.command()
async def stop(ctx):
    """Para a música atual"""
    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        ctx.voice_client.stop()
        await ctx.send("⏹️ Música parada!")

bot.run(TOKEN)
