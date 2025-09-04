# Imports
import discord
from discord.ext import commands, tasks
from discord.app_commands import command, describe, Range
import aiomysql
from datetime import datetime, timedelta
import random
import asyncio
import logging

# ========================================================================
# SISTEMA DE SORTEIOS - CONFIGURAÇÕES EDITÁVEIS
# ========================================================================
#
# ATENÇÃO: Esta seção contém todas as configurações que podem ser alteradas
# por administradores que não são programadores. Altere apenas os VALORES,
# não remova as aspas ou símbolos especiais.
#
# IMPORTANTE: Você deve preencher TODOS os campos abaixo antes de usar o bot!
#
# ========================================================================

# --- CONFIGURAÇÕES DO CANAL DE SORTEIOS ---
# ID do canal onde os sorteios serão realizados
# Para obter o ID: Clique com botão direito no canal > Copiar ID
CANAL_SORTEIOS_ID = 0  # SUBSTITUA pelo ID do seu canal de sorteios

# --- PERMISSÕES PARA CRIAR SORTEIOS ---
# IDs dos cargos que podem criar sorteios
# Para obter o ID: Clique com botão direito no cargo > Copiar ID
# NOTA: Usuários com permissão de Administrador SEMPRE podem criar sorteios
ALLOWED_GIVEAWAY_CREATOR_ROLES = [
    # ADICIONE AQUI OS IDs DOS CARGOS QUE PODEM CRIAR SORTEIOS
    # Exemplo: 1234567890123456789,
    # Exemplo: 1234567890123456790,
    # Exemplo: 1234567890123456791,
]

# --- CONFIGURAÇÕES DO BANCO DE DADOS MYSQL ---
# IMPORTANTE: Preencha com suas próprias credenciais do MySQL
# Estas informações são necessárias para o funcionamento dos sorteios
DB_CONFIG = {
    "host": "",  # SUBSTITUA pelo endereço do seu servidor MySQL (ex: "localhost")
    "user": "",  # SUBSTITUA pelo nome do usuário MySQL
    "password": "",  # SUBSTITUA pela senha do usuário MySQL
    "db": "",  # SUBSTITUA pelo nome do banco de dados
    "autocommit": True,
    "cursorclass": "DictCursor",
    "minsize": 1,
    "maxsize": 10
}

# --- CONFIGURAÇÕES DE TEMPO ---
# Tempo mínimo em minutos para um sorteio (não altere se não souber)
TEMPO_MINIMO_SORTEIO = 1

# Tempo máximo em minutos para um sorteio (deixe None para sem limite)
TEMPO_MAXIMO_SORTEIO = None  # None = sem limite, ou coloque um número como 1440 (24 horas)

# --- CONFIGURAÇÕES DE PARTICIPANTES ---
# Número máximo de ganhadores por sorteio
MAX_GANHADORES_SORTEIO = 25

# Número máximo de convites que podem ser exigidos
MAX_CONVITES_NECESSARIOS = 100

# --- MENSAGENS PERSONALIZADAS ---
# Mensagens que aparecem para os usuários (mantenha as aspas duplas)

# Mensagem quando alguém não tem permissão para criar sorteios
MENSAGEM_SEM_PERMISSAO = "❌ Você não tem permissão para criar sorteios."

# Mensagem quando alguém já está participando
MENSAGEM_JA_PARTICIPANDO = "Você já está participando deste sorteio!"

# Mensagem quando alguém participa com sucesso
MENSAGEM_PARTICIPACAO_SUCESSO = "✅ Você entrou no sorteio com sucesso!"

# Mensagem quando o sorteio é criado com sucesso
MENSAGEM_SORTEIO_CRIADO = "✅ Sorteio iniciado com sucesso em {canal}!"

# Mensagem quando não tem convites suficientes
MENSAGEM_CONVITES_INSUFICIENTES = """❌ **Requisito não cumprido!**
Este sorteio exige **{necessarios}** convites.
Você tem atualmente **{atual}** convites."""

# --- CONFIGURAÇÕES DE CORES ---
# Cores dos embeds (use nomes em inglês ou códigos hex)
COR_SORTEIO_ATIVO = "gold"        # Cor quando o sorteio está ativo
COR_SORTEIO_FINALIZADO = "green"  # Cor quando há vencedores
COR_SORTEIO_SEM_PARTICIPANTES = "red"  # Cor quando não há participantes

# --- CONFIGURAÇÕES DE EMOJIS ---
# Emojis usados nas mensagens (mantenha entre aspas duplas)
EMOJI_PRESENTE = "🎁"
EMOJI_TROFEU = "🏆"
EMOJI_INGRESSO = "🎟️"
EMOJI_RELOGIO = "⏰"
EMOJI_FESTA = "🎉"

# ========================================================================
# FIM DAS CONFIGURAÇÕES EDITÁVEIS
# ========================================================================
#
# ATENÇÃO: NÃO ALTERE NADA ABAIXO DESTA LINHA A MENOS QUE VOCÊ SEJA
# UM PROGRAMADOR EXPERIENTE!
#
# ========================================================================

# Configuração de logging
logger = logging.getLogger(__name__)

# --- Pool de Conexões ---
giveaway_connection_pool = None

async def init_giveaway_pool():
    global giveaway_connection_pool
    if giveaway_connection_pool: return

    # Verifica se as credenciais foram configuradas
    if not DB_CONFIG["host"] or not DB_CONFIG["user"] or not DB_CONFIG["password"] or not DB_CONFIG["db"]:
        logger.error("❌ GIVEAWAYS COG: Credenciais do MySQL não configuradas! Preencha o DB_CONFIG no topo do arquivo.")
        return

    try:
        config = DB_CONFIG.copy()
        config["cursorclass"] = aiomysql.cursors.DictCursor
        giveaway_connection_pool = await aiomysql.create_pool(**config)
        logger.info("✅ GIVEAWAYS COG: Pool de conexões MySQL inicializado.")
    except Exception as e:
        logger.error(f"❌ GIVEAWAYS COG: ERRO ao inicializar pool: {e}")

# --- Classe da View do Botão de Participação (COM INTEGRAÇÃO) ---
class GiveawayView(discord.ui.View):
    def __init__(self, bot_instance: commands.Bot, **kwargs):
        super().__init__(timeout=None) # Views persistentes não devem ter timeout
        self.bot = bot_instance
        # Adiciona os dados do sorteio diretamente na view para fácil acesso
        self.convites_necessarios = kwargs.get("convites_necessarios", 0)

        # Atualiza o label do botão
        button = self.children[0]
        if isinstance(button, discord.ui.Button):
            button.label = f"Participar ({kwargs.get('participants_count', 0)})"

    @discord.ui.button(label="Participar (0)", style=discord.ButtonStyle.primary, custom_id="participar_sorteio_com_invites")
    async def participate_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if not giveaway_connection_pool:
            return await interaction.followup.send("Erro: Serviço de sorteios indisponível.", ephemeral=True)

        try:
            async with giveaway_connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Pega dados do sorteio pelo ID da mensagem
                    await cursor.execute("SELECT * FROM sorteios WHERE mensagem_id = %s AND ativo = TRUE", (interaction.message.id,))
                    sorteio_db = await cursor.fetchone()

                    if not sorteio_db:
                        return await interaction.followup.send("Este sorteio não está mais ativo.", ephemeral=True)

                    # --- VERIFICAÇÃO DE CONVITES (A INTEGRAÇÃO) ---
                    convites_necessarios = sorteio_db.get("convites_necessarios", 0)
                    if convites_necessarios > 0:
                        invites_cog = self.bot.get_cog("Invites")
                        if not invites_cog:
                            logger.error("❌ CRÍTICO: O Cog \'Invites\' não foi encontrado para verificação.")
                            return await interaction.followup.send("Erro: Não foi possível verificar seus convites. Contate um admin.", ephemeral=True)

                        # Chama o método público do outro cog
                        user_invites = await invites_cog.get_user_invite_count(interaction.user.id)

                        if user_invites < convites_necessarios:
                            return await interaction.followup.send(
                                MENSAGEM_CONVITES_INSUFICIENTES.format(
                                    necessarios=convites_necessarios,
                                    atual=user_invites
                                ),
                                ephemeral=True
                            )
                    # --- FIM DA VERIFICAÇÃO ---

                    # Verifica se já está participando
                    await cursor.execute("SELECT * FROM participantes WHERE sorteio_id = %s AND usuario_id = %s", (sorteio_db["id"], interaction.user.id))
                    if await cursor.fetchone():
                        return await interaction.followup.send(MENSAGEM_JA_PARTICIPANDO, ephemeral=True)

                    # Adiciona participante
                    await cursor.execute("INSERT INTO participantes (sorteio_id, usuario_id, data_registro) VALUES (%s, %s, NOW())", (sorteio_db["id"], interaction.user.id))

                    # Atualiza contagem no botão
                    await cursor.execute("SELECT COUNT(*) AS total FROM participantes WHERE sorteio_id = %s", (sorteio_db["id"],))
                    total_participantes = (await cursor.fetchone())["total"]
                    button.label = f"Participar ({total_participantes})"
                    await interaction.message.edit(view=self)

                    await interaction.followup.send(MENSAGEM_PARTICIPACAO_SUCESSO, ephemeral=True)

        except Exception as e:
            logger.error(f"❌ ERRO no participate_button_callback: {e}", exc_info=True)
            await interaction.followup.send("Ocorreu um erro ao processar sua participação.", ephemeral=True)

# --- Classe do Cog de Sorteios ---
class GiveawaysCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Verifica se as configurações estão preenchidas
        if CANAL_SORTEIOS_ID == 0:
            logger.error("❌ GIVEAWAYS COG: CANAL_SORTEIOS_ID não configurado! Defina o ID do canal no topo do arquivo.")

        # Não verifica mais se ALLOWED_GIVEAWAY_CREATOR_ROLES está vazio, pois admins sempre podem criar

        # Registra a view uma única vez. O custom_id deve ser único.
        self.bot.add_view(GiveawayView(self.bot))
        self.is_cog_ready = asyncio.Event()
        if not hasattr(bot, "_giveaways_cog_setup_done"):
            bot._giveaways_cog_setup_done = True
            self.bot.loop.create_task(self.async_init())

    async def async_init(self):
        await self.bot.wait_until_ready()
        await init_giveaway_pool()
        await self._create_giveaways_tables()
        await self._load_and_update_active_giveaways()
        if not self.check_for_ended_giveaways.is_running():
            self.check_for_ended_giveaways.start()
        self.is_cog_ready.set()

    def cog_unload(self):
        self.check_for_ended_giveaways.cancel()

    async def _create_giveaways_tables(self):
        if not giveaway_connection_pool: return
        try:
            async with giveaway_connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS sorteios (
                            id INT AUTO_INCREMENT PRIMARY KEY, premio VARCHAR(255) NOT NULL,
                            data_fim DATETIME NOT NULL, canal_id BIGINT NOT NULL,
                            mensagem_id BIGINT DEFAULT NULL, ativo BOOLEAN NOT NULL DEFAULT TRUE,
                            num_ganhadores INT NOT NULL DEFAULT 1, vencedores_ids TEXT DEFAULT NULL,
                            convites_necessarios INT DEFAULT 0
                        );
                    """)
                    # Adiciona a coluna convites_necessarios se ela não existir
                    await cursor.execute("""
                        ALTER TABLE sorteios
                        ADD COLUMN convites_necessarios INT DEFAULT 0;
                    """)
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS participantes (
                            sorteio_id INT NOT NULL, usuario_id BIGINT NOT NULL,
                            data_registro DATETIME NOT NULL, PRIMARY KEY (sorteio_id, usuario_id),
                            FOREIGN KEY (sorteio_id) REFERENCES sorteios(id) ON DELETE CASCADE
                        );
                    """)
            logger.info("✅ GIVEAWAYS COG: Tabelas verificadas/criadas (com coluna de convites).")
        except Exception as e:
            # Ignora o erro se a coluna já existe
            if "Duplicate column name \'convites_necessarios\'" in str(e):
                logger.warning("⚠️ GIVEAWAYS COG: Coluna \'convites_necessarios\' já existe. Ignorando erro.")
            else:
                logger.error(f"❌ ERRO ao criar tabelas de sorteios: {e}", exc_info=True)

    async def _load_and_update_active_giveaways(self):
        """
        Verifica sorteios ativos no DB ao iniciar o Cog e agenda suas finalizações.
        Isso garante que os sorteios sobrevivam a uma reinicialização do bot.
        """
        if not giveaway_connection_pool: return

        try:
            async with giveaway_connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM sorteios WHERE ativo = TRUE")
                    active_giveaways = await cursor.fetchall()

                    count = 0
                    for sorteio in active_giveaways:
                        # Reagenda a finalização para cada sorteio ativo
                        self.bot.loop.create_task(self.schedule_giveaway_end(sorteio["id"], sorteio["data_fim"]))
                        count += 1
                    if count > 0:
                        logger.info(f"⚙️ GIVEAWAYS COG: {count} sorteio(s) ativo(s) foram recarregados e reagendados.")
                    else:
                        logger.info("⚙️ GIVEAWAYS COG: Nenhum sorteio ativo para recarregar.")

        except Exception as e:
            logger.error(f"❌ ERRO ao recarregar sorteios ativos: {e}", exc_info=True)

    async def schedule_giveaway_end(self, sorteio_id: int, end_time: datetime):
        """Agenda a finalização de um sorteio específico."""
        await self.bot.wait_until_ready()  # Garante que o bot está pronto

        # Calcula o tempo de espera em segundos
        now = datetime.now()
        delay = (end_time - now).total_seconds()

        if delay > 0:
            logger.info(f"⏰ Sorteio {sorteio_id} agendado para finalizar em {delay:.1f} segundos.")
            await asyncio.sleep(delay)

        # Bloco para finalizar o sorteio (similar ao seu loop atual)
        try:
            async with giveaway_connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Pega os dados mais recentes do sorteio
                    await cursor.execute("SELECT * FROM sorteios WHERE id = %s AND ativo = TRUE", (sorteio_id,))
                    sorteio = await cursor.fetchone()
                    if sorteio:
                        logger.info(f"🎯 Finalizando sorteio {sorteio_id} agendado.")
                        await self.end_giveaway(sorteio, cursor)
                    else:
                        logger.info(f"⚠️ Sorteio {sorteio_id} já foi finalizado ou não existe mais.")
        except Exception as e:
            logger.error(f"❌ ERRO ao finalizar sorteio agendado {sorteio_id}: {e}", exc_info=True)

    @command(name="sorteio", description="Inicia um novo sorteio.")
    @describe(
        premio="O que será sorteado?",
        tempo_minutos="Em quantos minutos o sorteio termina?",
        num_ganhadores="Quantas pessoas podem ganhar?",
        convites_necessarios="Número de convites necessários para participar."
    )
    async def sorteio(self, interaction: discord.Interaction, premio: str, tempo_minutos: Range[int, TEMPO_MINIMO_SORTEIO, TEMPO_MAXIMO_SORTEIO], num_ganhadores: Range[int, 1, MAX_GANHADORES_SORTEIO] = 1, convites_necessarios: Range[int, 0, MAX_CONVITES_NECESSARIOS] = 0):
        await self.is_cog_ready.wait()

        # Verifica se as configurações foram definidas
        if CANAL_SORTEIOS_ID == 0:
            return await interaction.response.send_message("❌ Erro: Canal de sorteios não configurado. Contate um administrador.", ephemeral=True)

        # Verifica permissões: Administradores OU cargos específicos
        has_permission = False

        # Primeira verificação: É administrador?
        if interaction.user.guild_permissions.administrator:
            has_permission = True
        # Segunda verificação: Tem algum dos cargos permitidos?
        elif interaction.user.roles and ALLOWED_GIVEAWAY_CREATOR_ROLES:
            has_permission = any(role.id in ALLOWED_GIVEAWAY_CREATOR_ROLES for role in interaction.user.roles)

        if not has_permission:
            return await interaction.response.send_message(MENSAGEM_SEM_PERMISSAO, ephemeral=True)

        canal_sorteio = self.bot.get_channel(CANAL_SORTEIOS_ID)
        if not canal_sorteio:
            return await interaction.response.send_message(f"Erro: Canal de sorteios não encontrado.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        data_fim = datetime.now() + timedelta(minutes=tempo_minutos)

        try:
            async with giveaway_connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Insere o novo requisito no banco de dados
                    sql = "INSERT INTO sorteios (premio, data_fim, canal_id, num_ganhadores, convites_necessarios) VALUES (%s, %s, %s, %s, %s)"
                    await cursor.execute(sql, (premio, data_fim, CANAL_SORTEIOS_ID, num_ganhadores, convites_necessarios))
                    sorteio_id = cursor.lastrowid

            # Cria a view e o embed
            view = GiveawayView(self.bot, convites_necessarios=convites_necessarios)
            embed = discord.Embed(
                title=f"{EMOJI_PRESENTE} Sorteio de {premio} {EMOJI_PRESENTE}",
                description=f"Clique no botão **Participar** para concorrer!",
                color=getattr(discord.Color, COR_SORTEIO_ATIVO, discord.Color.gold)()
            )
            embed.add_field(name=f"{EMOJI_TROFEU} Ganhadores", value=str(num_ganhadores), inline=True)
            # Adiciona o campo de requisito de convites se for maior que zero
            if convites_necessarios > 0:
                embed.add_field(name=f"{EMOJI_INGRESSO} Requisito", value=f"**{convites_necessarios}** convites", inline=True)

            embed.add_field(name=f"{EMOJI_RELOGIO} Termina em", value=f"<t:{int(data_fim.timestamp())}:R>", inline=False)
            embed.set_footer(text=f"Sorteio ID: {sorteio_id}")

            message = await canal_sorteio.send(embed=embed, view=view)

            # Atualiza a mensagem_id no banco de dados
            async with giveaway_connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("UPDATE sorteios SET mensagem_id = %s WHERE id = %s", (message.id, sorteio_id))

            await interaction.followup.send(MENSAGEM_SORTEIO_CRIADO.format(canal=canal_sorteio.mention), ephemeral=True)

            # AGORA, AGENDE A FINALIZAÇÃO PRECISA
            self.bot.loop.create_task(self.schedule_giveaway_end(sorteio_id, data_fim))

        except Exception as e:
            logger.error(f"❌ ERRO ao criar sorteio: {e}", exc_info=True)
            await interaction.followup.send(f"Ocorreu um erro ao processar sua participação.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_for_ended_giveaways(self):
        """
        Loop de segurança que roda a cada minuto para pegar sorteios que possam ter sido perdidos.
        Agora funciona como um mecanismo de fallback, não como o método principal.
        """
        await self.is_cog_ready.wait()
        if not giveaway_connection_pool: return

        try:
            async with giveaway_connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM sorteios WHERE data_fim <= NOW() AND ativo = TRUE")
                    ended_sorteios = await cursor.fetchall()

                    for sorteio in ended_sorteios:
                        logger.warning(f"⚠️ FALLBACK: Finalizando sorteio {sorteio['id']} que foi perdido pelo agendamento.")
                        await self.end_giveaway(sorteio, cursor)
        except Exception as e:
            logger.error(f"❌ ERRO GERAL em check_for_ended_giveaways: {e}", exc_info=True)

    async def end_giveaway(self, sorteio: dict, cursor: aiomysql.cursors.DictCursor):
        """Lógica para finalizar um único sorteio."""
        sorteio_id = sorteio["id"]
        canal = self.bot.get_channel(sorteio["canal_id"])
        if not canal:
            logger.warning(f"⚠️ Canal {sorteio['canal_id']} não encontrado. Desativando sorteio {sorteio_id}.")
            await cursor.execute("UPDATE sorteios SET ativo = FALSE WHERE id = %s", (sorteio_id,))
            return

        # Selecionar vencedores
        await cursor.execute("SELECT usuario_id FROM participantes WHERE sorteio_id = %s", (sorteio_id,))
        participantes = [row["usuario_id"] for row in await cursor.fetchall()]

        vencedores = []
        if participantes:
            # Garante que não há mais vencedores do que participantes
            num_ganhadores = min(sorteio["num_ganhadores"], len(participantes))
            vencedores = random.sample(participantes, num_ganhadores)

            # Atualiza o sorteio como inativo e registra os vencedores
            vencedores_ids_str = ",".join(map(str, vencedores))
            await cursor.execute("UPDATE sorteios SET ativo = FALSE, vencedores_ids = %s WHERE id = %s", (vencedores_ids_str, sorteio_id))

            # Envia mensagem no canal do sorteio
            mensagem_sorteio = await canal.fetch_message(sorteio["mensagem_id"])
            if mensagem_sorteio:
                embed_final = discord.Embed(
                    title=f"{EMOJI_FESTA} Sorteio de {sorteio['premio']} FINALIZADO! {EMOJI_FESTA}",
                    color=getattr(discord.Color, COR_SORTEIO_FINALIZADO, discord.Color.green)()
                )
                vencedores_mencoes = ", ".join([f"<@{v}>" for v in vencedores])
                embed_final.description = f"Parabéns aos ganhadores: {vencedores_mencoes}!"
                embed_final.set_footer(text=f"Sorteio ID: {sorteio_id}")
                await mensagem_sorteio.edit(embed=embed_final, view=None) # Remove o botão
            else:
                logger.warning(f"⚠️ Mensagem do sorteio {sorteio['mensagem_id']} não encontrada no canal {canal.id}.")
        else:
            # Se não houver participantes, apenas desativa o sorteio
            await cursor.execute("UPDATE sorteios SET ativo = FALSE WHERE id = %s", (sorteio_id,))
            mensagem_sorteio = await canal.fetch_message(sorteio["mensagem_id"])
            if mensagem_sorteio:
                embed_final = discord.Embed(
                    title=f"❌ Sorteio de {sorteio['premio']} FINALIZADO! ❌",
                    description="Não houve participantes suficientes para este sorteio.",
                    color=getattr(discord.Color, COR_SORTEIO_SEM_PARTICIPANTES, discord.Color.red)()
                )
                embed_final.set_footer(text=f"Sorteio ID: {sorteio_id}")
                await mensagem_sorteio.edit(embed=embed_final, view=None) # Remove o botão
            else:
                logger.warning(f"⚠️ Mensagem do sorteio {sorteio['mensagem_id']} não encontrada no canal {canal.id}.")

        logger.info(f"✅ Sorteio {sorteio_id} finalizado. Vencedores: {vencedores}")


async def setup(bot):
    await bot.add_cog(GiveawaysCog(bot))

