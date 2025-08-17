import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import yt_dlp
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='h!', intents=intents)

# Variáveis para controlar o loop de música
loop_states = {}  # Dicionário para armazenar o estado de loop por servidor
current_songs = {}  # Dicionário para armazenar a música atual por servidor

# Configurações do yt_dlp
ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt'
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

        # Salva informações da música atual
        current_songs[ctx.guild.id] = {
            'url': url,
            'title': info.get('title', 'Desconhecido'),
            'stream_url': stream_url
        }

        def play_next(_):
            if ctx.guild.id in loop_states and loop_states[ctx.guild.id]:
                # Se o loop está ativado, toca a mesma música novamente
                asyncio.run_coroutine_threadsafe(play_song(ctx, stream_url, info.get('title', 'Desconhecido')), bot.loop)

        async def play_song(ctx, stream_url, title):
            if ctx.voice_client:
                source = discord.FFmpegPCMAudio(
                    stream_url,
                    before_options=ffmpeg_opts['before_options'],
                    options=ffmpeg_opts['options']
                )
                ctx.voice_client.play(source, after=play_next)
                await ctx.send(f"🔄 Tocando: {title}")

        # Inicia a reprodução
        if voice_client.is_playing():
            voice_client.stop()

        await play_song(ctx, stream_url, info.get('title', 'Desconhecido'))

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

@bot.command()
async def repeat(ctx, mode: str = None):
    """Controla o modo de repetição da música
    Uso: 
    !repeat on - Ativa o modo de repetição
    !repeat off - Desativa o modo de repetição
    !repeat status - Mostra o status atual do modo de repetição"""
    
    if mode is None or mode.lower() not in ['on', 'off', 'status']:
        await ctx.send("❌ Use `!repeat on`, `!repeat off` ou `!repeat status`")
        return

    if mode.lower() == 'status':
        status = loop_states.get(ctx.guild.id, False)
        await ctx.send(f"🔄 Modo de repetição está: {'**ATIVADO**' if status else '**DESATIVADO**'}")
        return

    loop_states[ctx.guild.id] = mode.lower() == 'on'
    await ctx.send(f"🔄 Modo de repetição {'**ATIVADO**' if mode.lower() == 'on' else '**DESATIVADO**'}")

@bot.command()
async def current(ctx):
    """Mostra informações sobre a música atual"""
    if ctx.guild.id in current_songs:
        song = current_songs[ctx.guild.id]
        status = "🔄 (Loop Ativado)" if loop_states.get(ctx.guild.id, False) else ""
        await ctx.send(f"🎵 Tocando: {song['title']} {status}")
    else:
        await ctx.send("❌ Nenhuma música está tocando no momento.")

@bot.command()
async def command(ctx):
    """Mostra todos os comandos disponíveis"""
    embed = discord.Embed(
        title="🎵 Comandos do Bot de Música",
        description="Aqui está a lista de todos os comandos disponíveis:",
        color=discord.Color.blue()
    )

    # Comandos de Reprodução
    embed.add_field(
        name="📱 Comandos de Reprodução",
        value=(
            "`h!play <url>` - Toca uma música do YouTube\n"
            "`h!pause` - Pausa a música atual\n"
            "`h!resume` - Continua a música pausada\n"
            "`h!stop` - Para a música atual\n"
        ),
        inline=False
    )

    # Comandos de Controle
    embed.add_field(
        name="⚙️ Comandos de Controle",
        value=(
            "`h!repeat on` - Ativa o modo de repetição\n"
            "`h!repeat off` - Desativa o modo de repetição\n"
            "`h!repeat status` - Mostra o status do modo de repetição\n"
            "`h!current` - Mostra a música atual\n"
            "`h!leave` - Desconecta o bot do canal de voz\n"
        ),
        inline=False
    )

    # Informações adicionais
    embed.add_field(
        name="ℹ️ Informações",
        value=(
            "`h!command` - Mostra esta mensagem\n"
        ),
        inline=False
    )

    # Rodapé
    embed.set_footer(text="Use h! antes de cada comando • Bot desenvolvido por Nicolas")

    await ctx.send(embed=embed)

bot.run(TOKEN)
