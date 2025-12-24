import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import json
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ================= CONFIG =================
DIAS_INATIVIDADE = 4
ARQUIVO_DADOS = "dados.json"

# ================= DADOS =================
mensagens = {}      # {user_id: total_msgs}
ultima_msg = {}     # {user_id: iso_datetime}
canais_validos = set()  # canais que CONTAM presença


# ================= UTIL =================
def salvar_dados():
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump({
            "mensagens": mensagens,
            "ultima_msg": ultima_msg,
            "canais_validos": list(canais_validos)
        }, f, indent=4)


def carregar_dados():
    global mensagens, ultima_msg, canais_validos

    if not os.path.exists(ARQUIVO_DADOS):
        return

    with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
        dados = json.load(f)

    mensagens = {int(k): v for k, v in dados.get("mensagens", {}).items()}
    ultima_msg = {
        int(k): datetime.fromisoformat(v)
        for k, v in dados.get("ultima_msg", {}).items()
    }
    canais_validos = set(dados.get("canais_validos", []))


# ================= EVENTOS =================
@bot.event
async def on_ready():
    carregar_dados()
    print(f'Bot logado como {bot.user}')


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id not in canais_validos:
        await bot.process_commands(message)
        return

    user_id = message.author.id
    agora = datetime.now(timezone.utc)

    mensagens[user_id] = mensagens.get(user_id, 0) + 1
    ultima_msg[user_id] = agora

    salvar_dados()
    await bot.process_commands(message)


# ================= COMANDOS =================
@bot.command()
async def oi(ctx):
    await ctx.send(f'Oi {ctx.author.name}! Estou vivo 😎')


@bot.command(name="adicionarcanal")
@commands.has_permissions(administrator=True)
async def adicionar_canal(ctx):
    canais_validos.add(ctx.channel.id)
    salvar_dados()
    await ctx.send("✅ Este canal agora CONTA presença.")


@bot.command(name="removercanal")
@commands.has_permissions(administrator=True)
async def remover_canal(ctx):
    canais_validos.discard(ctx.channel.id)
    salvar_dados()
    await ctx.send("🚫 Este canal NÃO conta presença.")


@bot.command(name="mensagens")
async def mensagens_cmd(ctx, membro: discord.Member):
    total = mensagens.get(membro.id, 0)
    await ctx.send(f'{membro.name} enviou {total} mensagens válidas.')


@bot.command()
async def inatividade(ctx, membro: discord.Member):
    agora = datetime.now(timezone.utc)

    if membro.id not in ultima_msg:
        await ctx.send(f'{membro.name} nunca falou em canais válidos.')
        return

    diff = agora - ultima_msg[membro.id]
    dias = diff.days
    horas, resto = divmod(diff.seconds, 3600)
    minutos, _ = divmod(resto, 60)

    await ctx.send(
        f'{membro.name} está sem falar há {dias}d {horas}h {minutos}m.'
    )


@bot.command()
async def lista(ctx):
    agora = datetime.now(timezone.utc)
    limite = timedelta(days=DIAS_INATIVIDADE)

    inativos = []

    for member in ctx.guild.members:
        if member.bot:
            continue

        if member.id not in ultima_msg:
            inativos.append(member.name)
        else:
            if agora - ultima_msg[member.id] >= limite:
                inativos.append(member.name)

    if not inativos:
        await ctx.send("🎉 Nenhum membro inativo!")
    else:
        texto = "\n".join(inativos)
        await ctx.send(
            f"📋 Membros inativos há {DIAS_INATIVIDADE} dias ou mais:\n{texto}"
        )


# ================= START =================
bot.run(os.getenv("DISCORD_TOKEN"))
