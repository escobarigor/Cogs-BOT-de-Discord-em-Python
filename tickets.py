import discord
from discord.ext import commands
import asyncio
import mysql.connector

# ========================================================================
# SISTEMA DE TICKETS - CONFIGURAÇÕES EDITÁVEIS
# ========================================================================
#
# ATENÇÃO: Esta seção contém todas as configurações que podem ser alteradas
# por administradores que não são programadores. Altere apenas os VALORES,
# não remova as aspas ou símbolos especiais.
#
# IMPORTANTE: Você deve preencher TODOS os campos abaixo antes de usar o bot!
#
# ========================================================================

# --- CONFIGURAÇÃO DO BANCO DE DADOS MYSQL ---
# IMPORTANTE: Preencha com suas próprias credenciais do MySQL
# Estas informações são necessárias para o funcionamento dos tickets
DB_CONFIG = {
    "host": "",  # SUBSTITUA pelo endereço do seu servidor MySQL (ex: "localhost")
    "user": "",  # SUBSTITUA pelo nome do usuário MySQL
    "password": "",  # SUBSTITUA pela senha do usuário MySQL
    "database": "",  # SUBSTITUA pelo nome do banco de dados
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci"
}

# --- CONFIGURAÇÕES DOS CANAIS ---
# ID do canal onde a mensagem de setup será enviada
# Para obter o ID: Clique com botão direito no canal > Copiar ID
SETUP_CHANNEL_ID = 0000000000000000000  # SUBSTITUA pelo ID do seu canal

# --- IDS DAS CATEGORIAS DOS TICKETS ---
# Substitua pelos IDs das suas categorias do Discord
# Para obter o ID: Clique com botão direito na categoria > Copiar ID
TICKET_CATEGORIES = {
    "Geral": 0000000000000000000,      # SUBSTITUA pelo ID da categoria Geral
    "Denúncias": 0000000000000000000,  # SUBSTITUA pelo ID da categoria Denúncias
    "Financeiro": 0000000000000000000, # SUBSTITUA pelo ID da categoria Financeiro
    "Outros": 0000000000000000000      # SUBSTITUA pelo ID da categoria Outros
}

# ID da categoria onde tickets resolvidos serão movidos
RESOLVED_TICKET_CATEGORY_ID = 0000000000000000000  # SUBSTITUA pelo ID da categoria de tickets resolvidos

# --- PERMISSÕES DOS CARGOS ---
# IDs dos cargos que podem ver cada tipo de ticket
# Para obter o ID: Clique com botão direito no cargo > Copiar ID
TICKET_PERMISSIONS = {
    "Geral": [0000000000000000000, 0000000000000000000],      # SUBSTITUA pelos IDs dos cargos
    "Denúncias": [0000000000000000000, 0000000000000000000],  # SUBSTITUA pelos IDs dos cargos
    "Financeiro": [0000000000000000000],                      # SUBSTITUA pelos IDs dos cargos
    "Outros": [0000000000000000000, 0000000000000000000]      # SUBSTITUA pelos IDs dos cargos
}

# --- CONFIGURAÇÕES DE FIGURINHA ---
# ID da figurinha a ser usada no ticket (0 para desabilitar)
# Para obter o ID: Envie a figurinha em um canal e inspecione o JSON da mensagem
STICKER_ID = 0  # SUBSTITUA 0 pelo ID da sua figurinha ou deixe 0 para desabilitar

# --- CONFIGURAÇÕES DE MENSAGENS ---
# Mensagens que aparecem para os usuários (mantenha as aspas duplas)

# Título do sistema de atendimento
TITULO_ATENDIMENTO = "Atendimento - Seu Servidor"

# Descrição da mensagem de atendimento
DESCRICAO_ATENDIMENTO = """Bem-vindo ao atendimento do Seu Servidor

Escolha um assunto e um canal será aberto para contato com nossa equipe..

``O mal uso poderá resultar em punição.``"""

# Mensagem de boas-vindas no ticket
MENSAGEM_BOAS_VINDAS_TICKET = "Seja bem-vindo ao seu ticket de suporte!"

# Título do embed do ticket
TITULO_TICKET = "Atendimento | Ticket #{numero}"

# Descrição do embed do ticket
DESCRICAO_TICKET = """Use este canal para resolver seu problema.

**Dica:** Informe seu nick e o motivo do ticket para agilizar o atendimento."""

# Rodapé do embed do ticket
RODAPE_TICKET = "Ticket aberto por {usuario}"

# Mensagem quando ticket é fechado
MENSAGEM_TICKET_FECHADO = "{usuario} fechou este ticket. Ele foi movido para 'Tickets Resolvidos'.\n**Clique no botão abaixo novamente para excluí-lo definitivamente.**"

# Mensagem de confirmação de exclusão
MENSAGEM_CONFIRMACAO_EXCLUSAO = "{usuario} confirmou a exclusão do ticket. Este canal será deletado em 5 segundos."

# --- CONFIGURAÇÕES DE CORES ---
# Cores dos embeds (use nomes em inglês ou códigos hex)
COR_EMBED_TICKET = "orange"  # Cor do embed do ticket

# ========================================================================
# FIM DAS CONFIGURAÇÕES EDITÁVEIS
# ========================================================================
#
# ATENÇÃO: NÃO ALTERE NADA ABAIXO DESTA LINHA A MENOS QUE VOCÊ SEJA
# UM PROGRAMADOR EXPERIENTE!
#
# ========================================================================

def get_db_connection():
    """Função para estabelecer a conexão com o banco de dados."""
    try:
        # Verifica se as credenciais foram configuradas
        if not DB_CONFIG["host"] or not DB_CONFIG["user"] or not DB_CONFIG["database"]:
            print("❌ ERRO DB: Configurações do banco de dados não definidas. Configure DB_CONFIG no início do arquivo.")
            return None

        config = DB_CONFIG.copy()
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print(f"❌ ERRO DB: Não foi possível conectar ao banco de dados: {err}")
        return None

def create_tickets_table():
    """Função para criar a tabela 'tickets' se ela não existir e adicionar colunas/restrições se ausentes."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            print("⚙️ DB Setup: Tentando criar/verificar a tabela 'tickets'...")
            # Tenta criar a tabela com a estrutura completa
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    channel_id BIGINT UNIQUE,
                    user_id BIGINT NOT NULL,
                    ticket_type VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'open'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            conn.commit()
            print("✅ DB Setup: Comando CREATE TABLE IF NOT EXISTS executado.")

            # --- Lógica para verificar e adicionar colunas/restrições que podem ter sido ignoradas ---
            # Isso é crucial se a tabela já existia e não tinha a estrutura completa.

            # 1. Verificar e adicionar a coluna 'status'
            try:
                # Tenta selecionar algo para verificar a existência da coluna
                cursor.execute("SELECT status FROM tickets LIMIT 0") # LIMIT 0 para não retornar dados
                print("✅ DB Setup: Coluna 'status' já existe.")
            except mysql.connector.Error as err:
                if err.errno == 1054: # ER_BAD_FIELD_ERROR (Unknown column 'status')
                    print("⚠️ DB Setup: Coluna 'status' não encontrada. Adicionando...")
                    try:
                        cursor.execute("ALTER TABLE tickets ADD COLUMN status VARCHAR(50) DEFAULT 'open'")
                        conn.commit()
                        print("✅ DB Setup: Coluna 'status' adicionada com sucesso.")
                    except mysql.connector.Error as add_err:
                        print(f"❌ DB Setup: Erro ao tentar adicionar coluna 'status': {add_err}")
                        # Isso pode acontecer se a coluna foi adicionada por outra via mas a verificação falhou
                else:
                    print(f"❌ DB Setup: Erro inesperado ao verificar coluna 'status': {err}")
                    # Re-lança para não mascarar outros problemas
                    raise err
            finally:
                # Garante que qualquer resultado pendente da SELECT ou ALTER é consumido
                if cursor.with_rows: cursor.fetchall()


            # 2. Verificar e adicionar a restrição UNIQUE para 'channel_id'
            # (Se o CREATE TABLE IF NOT EXISTS não a criou)
            try:
                # Tenta adicionar a restrição. Se ela já existe, dará o erro 1061.
                cursor.execute("ALTER TABLE tickets ADD CONSTRAINT UQ_channel_id UNIQUE (channel_id)")
                conn.commit()
                print("✅ DB Setup: Restrição UNIQUE para 'channel_id' adicionada com sucesso.")
            except mysql.connector.Error as err:
                if err.errno == 1061: # ER_DUP_KEYNAME (Duplicate key name)
                    print("⚠️ DB Setup: Restrição UNIQUE para 'channel_id' já existe.")
                else:
                    print(f"❌ DB Setup: Erro inesperado ao adicionar restrição UNIQUE para 'channel_id': {err}")
                    # Re-lança para não mascarar outros problemas
                    raise err
            finally:
                # Garante que qualquer resultado pendente da ALTER é consumido
                if cursor.with_rows: cursor.fetchall()


            # 3. Verificar e adicionar a coluna 'id' como PRIMARY KEY AUTO_INCREMENT
            # Isso é o mais crítico e o motivo do 'Unknown column id'
            try:
                # Tenta selecionar algo para verificar a existência da coluna 'id'
                cursor.execute("SELECT id FROM tickets LIMIT 0")
                print("✅ DB Setup: Coluna 'id' (PK) já existe.")
            except mysql.connector.Error as err:
                if err.errno == 1054: # ER_BAD_FIELD_ERROR (Unknown column 'id')
                    print("⚠️ DB Setup: Coluna 'id' (PK) não encontrada. Adicionando...")
                    try:
                        # Adiciona a coluna id e define como PRIMARY KEY AUTO_INCREMENT
                        # Pode ser necessário adicionar um DEFAULT temporário se a tabela já tiver dados e NOT NULL.
                        cursor.execute("ALTER TABLE tickets ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST")
                        conn.commit()
                        print("✅ DB Setup: Coluna 'id' (PK) adicionada com sucesso.")
                    except mysql.connector.Error as add_err:
                        print(f"❌ DB Setup: Erro ao tentar adicionar coluna 'id': {add_err}")
                        # Se der erro aqui, é um problema sério, pode ser duplicidade de PK, etc.
                        raise add_err
                else:
                    print(f"❌ DB Setup: Erro inesperado ao verificar coluna 'id': {err}")
                    raise err
            finally:
                if cursor.with_rows: cursor.fetchall() # Consome resultados pendentes

            print("✅ DB Setup: Tabela 'tickets' verificada/ajustada com sucesso.")

        except mysql.connector.Error as err:
            print(f"❌ ERRO DB: Falha geral durante o setup da tabela 'tickets': {err}")
            # Tenta um rollback em caso de falha geral
            try:
                conn.rollback()
                print("⚠️ DB Setup: Rollback realizado devido a erro.")
            except Exception as rb_err:
                print(f"❌ DB Setup: Erro ao tentar realizar rollback: {rb_err}")
        finally:
            # Garante que o cursor e a conexão sejam fechados de forma segura
            if cursor:
                try:
                    if cursor.with_rows: cursor.fetchall()
                    cursor.close()
                except mysql.connector.Error as close_err:
                    print(f"⚠️ DB Cleanup: Erro ao fechar cursor: {close_err}")
            if conn:
                try:
                    conn.close()
                except mysql.connector.Error as close_err:
                    print(f"⚠️ DB Cleanup: Erro ao fechar conexão: {close_err}")
    else:
        print("⚠️ DB: Não foi possível conectar ao banco de dados para o setup.")

# Chamar a função para criar a tabela e verificar colunas quando o bot iniciar
create_tickets_table()

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Geral", description="Reporte bugs, falhas ou suporte generalizado", emoji="❤️"),
            discord.SelectOption(label="Denúncias", description="Viu algum jogador suspeito? Esta é a área", emoji="🔥"),
            discord.SelectOption(label="Financeiro", description="Problemas com produtos ou compras no site", emoji="💎"),
            discord.SelectOption(label="Outros", description="Para qualquer outro assunto não listado acima", emoji="👻")
        ]
        super().__init__(placeholder="Selecione uma categoria", options=options)

    async def callback(self, interaction: discord.Interaction):
        print(f"🔄 TICKETS: Usuário {interaction.user.name} ({interaction.user.id}) selecionou ticket: {self.values[0]}.")
        await interaction.response.defer(ephemeral=True) # Responde ephemerally para o usuário que clicou
        guild = interaction.guild
        selected_type = self.values[0]

        category_id = TICKET_CATEGORIES.get(selected_type)
        category = discord.utils.get(guild.categories, id=category_id)

        if category is None:
            await interaction.followup.send("Categoria de tickets não encontrada. Verifique o ID da categoria.", ephemeral=True)
            print(f"❌ TICKETS: Categoria '{selected_type}' não encontrada para ticket de {interaction.user.name}.")
            return

        try:
            # Verifica se o usuário já tem um ticket aberto
            user_has_open_ticket = False
            conn_check_open = get_db_connection()
            if conn_check_open:
                cursor_check_open = conn_check_open.cursor(dictionary=True)
                try:
                    cursor_check_open.execute(
                        "SELECT channel_id FROM tickets WHERE user_id = %s AND status = 'open'",
                        (interaction.user.id,)
                    )
                    existing_ticket_data = cursor_check_open.fetchone()
                    if existing_ticket_data:
                        existing_channel = guild.get_channel(existing_ticket_data["channel_id"])
                        # Verifica se o canal ainda existe no Discord e pertence à categoria de tickets
                        if existing_channel and existing_channel.category_id in TICKET_CATEGORIES.values():
                            user_has_open_ticket = True
                            await interaction.followup.send(
                                f"Você já possui um ticket aberto em {existing_channel.mention}. Por favor, feche-o antes de abrir um novo.",
                                ephemeral=True
                            )
                            print(f"⚠️ TICKETS: {interaction.user.name} tentou abrir ticket, mas já possui um aberto.")
                except mysql.connector.Error as err:
                    print(f"❌ ERRO DB: Falha ao verificar tickets abertos no DB: {err}")
                    await interaction.followup.send("Ocorreu um erro ao verificar seus tickets existentes. Tente novamente mais tarde.", ephemeral=True)
                    return
                finally:
                    if cursor_check_open:
                        try:
                            if cursor_check_open.with_rows: cursor_check_open.fetchall()
                            cursor_check_open.close()
                        except mysql.connector.Error as close_err:
                            print(f"⚠️ DB Cleanup: Erro ao fechar cursor_check_open: {close_err}")
                    if conn_check_open:
                        try:
                            conn_check_open.close()
                        except mysql.connector.Error as close_err:
                            print(f"⚠️ DB Cleanup: Erro ao fechar conn_check_open: {close_err}")
            else:
                await interaction.followup.send("Não foi possível conectar ao banco de dados para verificar tickets existentes. Tente novamente mais tarde.", ephemeral=True)
                print("❌ TICKETS: Falha ao obter conexão com o DB ao verificar tickets abertos.")
                return

            if user_has_open_ticket:
                return


            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            for role_id in TICKET_PERMISSIONS[selected_type]:
                role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True)
                else:
                    print(f"⚠️ TICKETS: Cargo com ID {role_id} para ticket '{selected_type}' não encontrado.")

            # Inserir ticket no banco de dados para obter o ticket_number ANTES de criar o canal
            # Inserimos apenas o user_id, ticket_type e status. O id (ticket_number) será gerado automaticamente.
            ticket_number = None
            conn_insert = get_db_connection()
            if conn_insert:
                cursor_insert = conn_insert.cursor()
                try:
                    cursor_insert.execute("INSERT INTO tickets (user_id, ticket_type, status) VALUES (%s, %s, %s)",
                                          (interaction.user.id, selected_type, "open"))
                    conn_insert.commit()
                    ticket_number = cursor_insert.lastrowid # Pega o ID gerado automaticamente (ex: 1, 2, 3)
                    print(f"✅ DB: Ticket temporário para {interaction.user.name} registrado no DB com ID: {ticket_number}.")
                except mysql.connector.Error as err:
                    print(f"❌ ERRO DB: Falha ao inserir ticket no DB para obter número: {err}")
                    await interaction.followup.send(f"Erro ao registrar o ticket no banco de dados. Tente novamente. ({err})", ephemeral=True)
                    return # Sai se não conseguir registrar no DB
                finally:
                    if cursor_insert:
                        try:
                            if cursor_insert.with_rows: cursor_insert.fetchall()
                            cursor_insert.close()
                        except mysql.connector.Error as close_err:
                            print(f"⚠️ DB Cleanup: Erro ao fechar cursor_insert: {close_err}")
                    if conn_insert:
                        try:
                            conn_insert.close()
                        except mysql.connector.Error as close_err:
                            print(f"⚠️ DB Cleanup: Erro ao fechar conn_insert: {close_err}")
            else:
                await interaction.followup.send("Não foi possível conectar ao banco de dados para gerar o número do ticket. Tente novamente mais tarde.", ephemeral=True)
                print("❌ TICKETS: Falha ao obter conexão com o DB ao criar ticket (pré-canal).")
                return

            # FORMATAR O NÚMERO DO TICKET COM ZEROS À ESQUERDA AQUI
            formatted_ticket_number = f"{ticket_number:04d}" # Ex: 1 vira "0001", 12 vira "0012"

            # Usa o formatted_ticket_number para nomear o canal
            # Remove acentos e caracteres especiais para nomes de canal
            # Adicionado tratamento para caracteres não ASCII para evitar erros no nome do canal
            clean_username = "".join(c for c in interaction.user.name if c.isalnum() or c == " ").lower().replace(" ", "-")
            # O Discord tem um limite para nomes de canal, vamos truncar se ficar muito longo
            if len(clean_username) > (100 - len(f"ticket-{formatted_ticket_number}-")):
                clean_username = clean_username[:(100 - len(f"ticket-{formatted_ticket_number}-"))]

            ticket_channel_name = f"ticket-{formatted_ticket_number}-{clean_username}"

            ticket_channel = await guild.create_text_channel(
                ticket_channel_name,
                category=category,
                topic=f"Ticket #{formatted_ticket_number} de {interaction.user.name} sobre {selected_type}",
                overwrites=overwrites
            )
            print(f"✅ TICKETS: Canal \'{ticket_channel.name}\' criado para ticket #{formatted_ticket_number}.")

            # Atualiza o registro do ticket no banco de dados com o channel_id
            conn_update_channel = get_db_connection()
            if conn_update_channel:
                cursor_update_channel = conn_update_channel.cursor()
                try:
                    cursor_update_channel.execute("UPDATE tickets SET channel_id = %s WHERE id = %s",
                                                  (ticket_channel.id, ticket_number)) # Usa o ticket_number original para o WHERE
                    conn_update_channel.commit()
                    print(f"✅ DB: Ticket {ticket_number} atualizado com channel_id: {ticket_channel.id}.")
                except mysql.connector.Error as err:
                    print(f"❌ ERRO DB: Falha ao atualizar channel_id para ticket {ticket_number} no DB: {err}")
                    await interaction.followup.send(f"Erro ao registrar o ID do canal no banco de dados. O ticket foi criado, mas pode não persistir corretamente. ({err})", ephemeral=True)
                finally:
                    if cursor_update_channel:
                        try:
                            if cursor_update_channel.with_rows: cursor_update_channel.fetchall()
                            cursor_update_channel.close()
                        except mysql.connector.Error as close_err:
                            print(f"⚠️ DB Cleanup: Erro ao fechar cursor_update_channel: {close_err}")
                    if conn_update_channel:
                        try:
                            conn_update_channel.close()
                        except mysql.connector.Error as close_err:
                            print(f"⚠️ DB Cleanup: Erro ao fechar conn_update_channel: {close_err}")
            else:
                await interaction.followup.send("Não foi possível conectar ao banco de dados para registrar o ID do canal. O ticket foi criado, mas pode não persistir corretamente.", ephemeral=True)
                print("❌ TICKETS: Falha ao obter conexão com o DB ao atualizar channel_id.")


            close_embed = discord.Embed(
                title=TITULO_TICKET.format(numero=formatted_ticket_number),
                description=DESCRICAO_TICKET,
                color=getattr(discord.Color, COR_EMBED_TICKET, discord.Color.orange)()
            )
            avatar_url = interaction.user.avatar.url if interaction.user.avatar else None
            close_embed.set_footer(
                text=RODAPE_TICKET.format(usuario=interaction.user.name),
                icon_url=avatar_url
            )

            close_button = discord.ui.Button(label="Fechar Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_ticket_{ticket_channel.id}")

            async def close_button_callback(close_interaction: discord.Interaction):
                print(f"🔄 TICKETS: Botão clicado por {close_interaction.user.name} em {close_interaction.channel.name}.")

                channel_id = close_interaction.channel.id
                original_user_id = None
                current_ticket_status = 'unknown'
                current_ticket_number = None # Para o número sequencial do ticket

                # Buscar informações do ticket no DB
                conn_fetch_info = get_db_connection()
                if conn_fetch_info:
                    cursor_fetch_info = conn_fetch_info.cursor(dictionary=True)
                    try:
                        cursor_fetch_info.execute("SELECT user_id, status, id FROM tickets WHERE channel_id = %s", (channel_id,))
                        fetched_info = cursor_fetch_info.fetchone()
                        if fetched_info:
                            original_user_id = fetched_info['user_id']
                            current_ticket_status = fetched_info['status']
                            current_ticket_number = fetched_info['id'] # Pega o ID gerado automaticamente
                        else:
                            print(f"⚠️ TICKETS: Ticket {channel_id} não encontrado no DB. Assumindo o usuário atual como criador e status 'open'.")
                            original_user_id = close_interaction.user.id # Fallback
                            current_ticket_status = 'open'
                    except mysql.connector.Error as err:
                        print(f"❌ ERRO DB: Falha ao buscar info do ticket para fechar/excluir: {err}")
                        original_user_id = close_interaction.user.id # Fallback em caso de erro DB
                        current_ticket_status = 'open'
                    finally:
                        if cursor_fetch_info:
                            try:
                                if cursor_fetch_info.with_rows: cursor_fetch_info.fetchall()
                                cursor_fetch_info.close()
                            except mysql.connector.Error as close_err:
                                print(f"⚠️ DB Cleanup: Erro ao fechar cursor_fetch_info: {close_err}")
                        if conn_fetch_info:
                            try:
                                conn_fetch_info.close()
                            except mysql.connector.Error as close_err:
                                print(f"⚠️ DB Cleanup: Erro ao fechar conn_fetch_info: {close_err}")
                else:
                    print("❌ TICKETS: Falha ao obter conexão com o DB ao buscar info do ticket para fechar/excluir.")
                    original_user_id = close_interaction.user.id # Fallback se não houver conexão
                    current_ticket_status = 'open'

                # Verifica permissão para fechar/excluir o ticket
                is_admin_or_moderator = close_interaction.user.guild_permissions.manage_channels
                if close_interaction.user.id != original_user_id and not is_admin_or_moderator:
                    await close_interaction.response.send_message("Você não tem permissão para interagir com este botão.", ephemeral=True)
                    return

                await close_interaction.response.defer(ephemeral=True)

                if current_ticket_status == 'open':
                    # Primeiro Clique: Mover para Resolvidos e alterar botão
                    try:
                        # Remove permissões de leitura/escrita do usuário criador do ticket
                        original_member = close_interaction.guild.get_member(original_user_id)
                        if original_member:
                            overwrites = close_interaction.channel.overwrites_for(original_member)
                            overwrites.read_messages = False
                            overwrites.send_messages = False
                            await close_interaction.channel.set_permissions(original_member, overwrite=overwrites)
                            print(f"🔄 TICKETS: Permissões de {original_member.name} removidas em {close_interaction.channel.name}.")


                        resolved_category = discord.utils.get(close_interaction.guild.categories, id=RESOLVED_TICKET_CATEGORY_ID)
                        if resolved_category:
                            await close_interaction.channel.edit(category=resolved_category)
                            print(f"✅ TICKETS: Ticket {close_interaction.channel.name} movido para \'Tickets Resolvidos\'.")

                        # Atualizar status no banco de dados para 'resolved'
                        conn_update = get_db_connection()
                        if conn_update:
                            cursor_update = conn_update.cursor()
                            try:
                                cursor_update.execute("UPDATE tickets SET status = 'resolved' WHERE channel_id = %s", (channel_id,))
                                conn_update.commit()
                                print(f"✅ DB: Status do ticket {channel_id} atualizado para 'resolved'.")
                            except mysql.connector.Error as err:
                                print(f"❌ ERRO DB: Falha ao atualizar status do ticket {channel_id} para 'resolved': {err}")
                            finally:
                                if cursor_update:
                                    try:
                                        if cursor_update.with_rows: cursor_update.fetchall()
                                        cursor_update.close()
                                    except mysql.connector.Error as close_err:
                                        print(f"⚠️ DB Cleanup: Erro ao fechar cursor_update: {close_err}")
                                if conn_update:
                                    try:
                                        conn_update.close()
                                    except mysql.connector.Error as close_err:
                                        print(f"⚠️ DB Cleanup: Erro ao fechar conn_update: {close_err}")
                        else:
                            print("❌ TICKETS: Falha ao obter conexão com o DB para atualizar status.")

                        await close_interaction.channel.send(MENSAGEM_TICKET_FECHADO.format(usuario=close_interaction.user.mention))

                        # Recria a view com o novo botão "Excluir Ticket"
                        new_close_button = discord.ui.Button(label="Excluir Ticket", style=discord.ButtonStyle.red, custom_id=f"delete_ticket_{channel_id}")
                        new_close_button.callback = close_button_callback # Atribui o mesmo callback para o próximo clique
                        new_view = discord.ui.View(timeout=None)
                        new_view.add_item(new_close_button)

                        # Tenta encontrar a mensagem original do bot para editar o botão
                        try:
                            bot_message_with_view = None
                            async for msg in close_interaction.channel.history(limit=5):
                                if msg.author == close_interaction.client.user and msg.components:
                                    for component_row in msg.components:
                                        for component in component_row.children:
                                            # Verifica o custom_id do botão
                                            if isinstance(component, discord.ui.Button) and component.custom_id in [f"close_ticket_{channel_id}", f"delete_ticket_{channel_id}"]:
                                                bot_message_with_view = msg
                                                break
                                        if bot_message_with_view:
                                            break
                                    if bot_message_with_view:
                                        break

                            if bot_message_with_view:
                                await bot_message_with_view.edit(view=new_view)
                                # Adiciona a view ao bot para persistência após a edição
                                self.bot.add_view(new_view, message_id=bot_message_with_view.id)
                                print(f"✅ TICKETS: Botão em {bot_message_with_view.id} atualizado para 'Excluir Ticket'.")
                            else:
                                # Se não encontrar a mensagem, envia uma nova com o botão de excluir
                                await close_interaction.channel.send("O ticket foi resolvido. Clique no botão abaixo para excluí-lo definitivamente.", view=new_view)
                                print(f"⚠️ TICKETS: Mensagem original do botão não encontrada. Nova mensagem com botão 'Excluir Ticket' enviada.")

                        except Exception as e:
                            print(f"❌ TICKETS: ERRO ao atualizar a mensagem do botão: {e}")
                            await close_interaction.channel.send("O ticket foi resolvido, mas houve um erro ao atualizar o botão. Clique no botão abaixo para excluí-lo definitivamente.", view=new_view)

                    except Exception as e:
                        await close_interaction.followup.send(f"Ocorreu um erro ao fechar o ticket: {str(e)}", ephemeral=True)
                        print(f"❌ TICKETS: ERRO ao fechar ticket {close_interaction.channel.name}: {str(e)}")

                elif current_ticket_status == 'resolved':
                    # Segundo Clique: Excluir o canal
                    try:
                        await close_interaction.channel.send(MENSAGEM_CONFIRMACAO_EXCLUSAO.format(usuario=close_interaction.user.mention))
                        print(f"🔄 TICKETS: Confirmação de exclusão para {close_interaction.channel.name}. Deletando canal.")
                        await asyncio.sleep(5)

                        # Remover ticket do banco de dados ANTES de deletar o canal
                        conn_delete = get_db_connection()
                        if conn_delete:
                            cursor_delete = conn_delete.cursor()
                            try:
                                # Deleta usando o channel_id
                                cursor_delete.execute("DELETE FROM tickets WHERE channel_id = %s", (channel_id,))
                                conn_delete.commit()
                                print(f"✅ DB: Ticket {channel_id} DELETADO do DB.")
                            except mysql.connector.Error as err:
                                print(f"❌ ERRO DB: Falha ao deletar ticket {channel_id} do DB: {err}")
                                await close_interaction.followup.send(f"Erro ao remover o ticket do banco de dados. Por favor, remova-o manualmente se necessário.", ephemeral=True)
                            finally:
                                if cursor_delete:
                                    try:
                                        if cursor_delete.with_rows: cursor_delete.fetchall()
                                        cursor_delete.close()
                                    except mysql.connector.Error as close_err:
                                        print(f"⚠️ DB Cleanup: Erro ao fechar cursor_delete: {close_err}")
                                if conn_delete:
                                    try:
                                        conn_delete.close()
                                    except mysql.connector.Error as close_err:
                                        print(f"⚠️ DB Cleanup: Erro ao fechar conn_delete: {close_err}")
                        else:
                            print("❌ TICKETS: Falha ao obter conexão com o DB para deletar ticket.")
                            await close_interaction.followup.send("Não foi possível conectar ao banco de dados para remover o ticket. Por favor, remova-o manualmente se necessário.", ephemeral=True)

                        await close_interaction.channel.delete(reason="Ticket excluído por solicitação do usuário/moderação.")
                        print(f"✅ TICKETS: Canal {close_interaction.channel.name} deletado do Discord.")

                    except discord.Forbidden:
                        await close_interaction.followup.send("Não tenho permissão para deletar este canal. Por favor, remova-o manualmente.", ephemeral=True)
                        print(f"❌ TICKETS: Permissão negada para deletar canal {close_interaction.channel.name}.")
                    except Exception as e:
                        await close_interaction.followup.send(f"Ocorreu um erro ao excluir o ticket: {str(e)}", ephemeral=True)
                        print(f"❌ TICKETS: ERRO ao excluir ticket {close_interaction.channel.name}: {str(e)}")
                else:
                    await close_interaction.followup.send("Este ticket está em um estado desconhecido. Por favor, contate um administrador.", ephemeral=True)
                    print(f"⚠️ TICKETS: Ticket {channel_id} em estado desconhecido: {actual_status}.")

            close_button.callback = close_button_callback

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup", description="Configura o sistema de tickets.")
    async def setup(self, interaction: discord.Interaction):
        print(f"🔄 CMD: Comando /setup acionado por {interaction.user.name} ({interaction.user.id}).")
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
            print(f"❌ CMD: /setup negado para {interaction.user.name} (sem permissão).")
            return

        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title=TITULO_ATENDIMENTO,
            description=DESCRICAO_ATENDIMENTO,
            color=getattr(discord.Color, COR_EMBED_TICKET, discord.Color.orange)()
        )
        ticket_view = discord.ui.View(timeout=None)
        ticket_view.add_item(TicketSelect())

        try:
            target_channel_id = SETUP_CHANNEL_ID
            target_channel = self.bot.get_channel(target_channel_id)
            if not target_channel:
                await interaction.followup.send(f"Canal de tickets (ID: {target_channel_id}) não encontrado.", ephemeral=True)
                print(f"❌ CMD: /setup falhou. Canal {target_channel_id} não encontrado.")
                return

            bot_member = target_channel.guild.me
            perms = target_channel.permissions_for(bot_member)
            if not perms.send_messages:
                await interaction.followup.send(f"Não tenho permissão para enviar mensagens no canal {target_channel.name}.", ephemeral=True)
                print(f"❌ CMD: /setup falhou. Permissão negada para enviar mensagens no canal {target_channel.name}.")
                return

            if perms.manage_messages:
                try:
                    def is_bot_setup_message(message):
                        return message.author == self.bot.user and message.embeds and message.embeds[0].title == TITULO_ATENDIMENTO

                    deleted_count = 0
                    async for message in target_channel.history(limit=50):
                        if is_bot_setup_message(message):
                            await message.delete()
                            deleted_count += 1
                    if deleted_count > 0:
                        print(f"✅ CMD: /setup removeu {deleted_count} mensagens de setup antigas no canal {target_channel.name}.")
                except discord.Forbidden:
                    print(f"❌ CMD: Permissão negada para purgar mensagens antigas do bot no canal {target_channel.name}.")
                except Exception as e:
                    print(f"❌ CMD: ERRO ao purgar mensagens antigas do bot no canal {target_channel.name}: {e}")

            await target_channel.send(embed=embed, view=ticket_view)
            await interaction.followup.send(f"Mensagem de setup de tickets enviada com sucesso no canal {target_channel.mention}!", ephemeral=True)
            print(f"✅ CMD: /setup concluído. Mensagem de ticket ENVIADA no canal {target_channel.name}.")

        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao enviar/atualizar a mensagem de setup: {str(e)}", ephemeral=True)
            print(f"❌ CMD: ERRO ao enviar/atualizar mensagem de setup no canal {interaction.channel.name}: {str(e)}")

    async def setup_ticket_message(self):
        """Função para ser chamada no on_ready para configurar a mensagem de tickets."""
        print("⚙️ SETUP_COG: Iniciando setup automático de tickets do cog...")

        ticket_channel = self.bot.get_channel(SETUP_CHANNEL_ID)

        if ticket_channel:
            bot_member = ticket_channel.guild.me
            perms = ticket_channel.permissions_for(bot_member)

            if not perms.manage_messages or not perms.send_messages:
                print(f"❌ SETUP_COG: Permissões insuficientes no canal {ticket_channel.name} (ID: {SETUP_CHANNEL_ID}) para limpar/enviar a mensagem de setup de tickets.")
            else:
                try:
                    def is_bot_setup_message(message):
                        return message.author == self.bot.user and message.embeds and message.embeds[0].title == TITULO_ATENDIMENTO

                    async for message in ticket_channel.history(limit=50):
                        if is_bot_setup_message(message):
                            await message.delete()
                    print(f"✅ SETUP_COG: Mensagens antigas no canal {ticket_channel.name} purgadas.")

                    embed = discord.Embed(
                        title=TITULO_ATENDIMENTO,
                        description=DESCRICAO_ATENDIMENTO,
                        color=getattr(discord.Color, COR_EMBED_TICKET, discord.Color.orange)()
                    )
                    ticket_view = discord.ui.View(timeout=None)
                    ticket_view.add_item(TicketSelect())
                    await ticket_channel.send(embed=embed, view=ticket_view)
                    print(f"✅ SETUP_COG: Mensagem de setup de tickets enviada com sucesso no canal {ticket_channel.name}.")

                except discord.Forbidden:
                    print(f"❌ SETUP_COG: Permissão negada para purgar/enviar mensagens no canal {ticket_channel.name}.")
                except Exception as e:
                    print(f"❌ SETUP_COG: ERRO ao limpar e configurar o canal de tickets: {e}")
        else:
            print(f"⚠️ SETUP_COG: Canal de tickets (ID: {SETUP_CHANNEL_ID}) não encontrado. Setup automático ignorado.")

    async def load_tickets_from_db(self):
        print("⚙️ SETUP_COG: Carregando tickets do banco de dados para reativar botões...")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                # Busca o 'id' (número sequencial) também
                cursor.execute("SELECT id, channel_id, user_id, ticket_type, status FROM tickets WHERE status IN ('open', 'resolved')")
                tickets_data = cursor.fetchall()
            except mysql.connector.Error as err:
                print(f"❌ ERRO DB: Falha ao carregar tickets do DB: {err}")
                tickets_data = []
            finally:
                if cursor:
                    try:
                        if cursor.with_rows: cursor.fetchall()
                        cursor.close()
                    except mysql.connector.Error as close_err:
                        print(f"⚠️ DB Cleanup: Erro ao fechar cursor na carga do DB: {close_err}")
                if conn:
                    try:
                        conn.close()
                    except mysql.connector.Error as close_err:
                        print(f"⚠️ DB Cleanup: Erro ao fechar conexão na carga do DB: {close_err}")
        else:
            print("❌ TICKETS: Falha ao obter conexão com o DB ao carregar tickets para reativar botões.")
            tickets_data = []

        for ticket in tickets_data:
            ticket_id = ticket["id"] # O número sequencial do ticket do DB
            channel_id = ticket["channel_id"]
            user_id = ticket["user_id"]
            ticket_type = ticket["ticket_type"]
            status = ticket["status"]

            channel = self.bot.get_channel(channel_id)
            if channel:
                # Re-formata o número do ticket para exibição no nome do canal ou embed se necessário
                formatted_ticket_number = f"{ticket_id:04d}"

                if status == "open":
                    button_label = "Fechar Ticket"
                    button_style = discord.ButtonStyle.danger
                    button_custom_id = f"close_ticket_{channel_id}"
                elif status == "resolved":
                    button_label = "Excluir Ticket"
                    button_style = discord.ButtonStyle.red
                    button_custom_id = f"delete_ticket_{channel_id}"
                else:
                    button_label = "Ticket (Erro)"
                    button_style = discord.ButtonStyle.gray
                    button_custom_id = f"error_ticket_{channel_id}"

                action_button = discord.ui.Button(label=button_label, style=button_style, custom_id=button_custom_id)

                async def action_button_callback_loaded(interaction: discord.Interaction, original_user_id=user_id, current_status=status, loaded_ticket_id=ticket_id):
                    print(f"🔄 TICKETS: Botão (carregado do DB) clicado por {interaction.user.name} em {interaction.channel.name}.")

                    channel_id_callback = interaction.channel.id # Pega o ID do canal da interação

                    is_admin_or_moderator = interaction.user.guild_permissions.manage_channels
                    if interaction.user.id != original_user_id and not is_admin_or_moderator:
                        await interaction.response.send_message("Você não tem permissão para interagir com este botão.", ephemeral=True)
                        return

                    await interaction.response.defer(ephemeral=True)

                    # Re-busca o status atual para garantir que não houve mudança externa
                    conn_recheck_status = get_db_connection()
                    actual_status = current_status # Assume o status carregado como padrão
                    if conn_recheck_status:
                        cursor_recheck_status = conn_recheck_status.cursor(dictionary=True)
                        try:
                            cursor_recheck_status.execute("SELECT status FROM tickets WHERE channel_id = %s", (channel_id_callback,))
                            rechecked_info = cursor_recheck_status.fetchone()
                            if rechecked_info:
                                actual_status = rechecked_info["status"]
                            else:
                                print(f"⚠️ TICKETS: Ticket {channel_id_callback} não encontrado no DB durante recheque de status. Tratando como 'open'.")
                                actual_status = "open" # Fallback
                        except mysql.connector.Error as err:
                            print(f"❌ ERRO DB: Falha ao re-verificar status do ticket {channel_id_callback}: {err}")
                        finally:
                            if cursor_recheck_status:
                                try:
                                    if cursor_recheck_status.with_rows: cursor_recheck_status.fetchall()
                                    cursor_recheck_status.close()
                                except mysql.connector.Error as close_err:
                                    print(f"⚠️ DB Cleanup: Erro ao fechar cursor_recheck_status: {close_err}")
                            if conn_recheck_status:
                                try:
                                    conn_recheck_status.close()
                                except mysql.connector.Error as close_err:
                                    print(f"⚠️ DB Cleanup: Erro ao fechar conn_recheck_status: {close_err}")
                    else:
                        print("❌ TICKETS: Falha ao obter conexão com o DB para re-verificar status.")


                    if actual_status == "open":
                        try:
                            original_member = interaction.guild.get_member(original_user_id)
                            if original_member:
                                overwrites = interaction.channel.overwrites_for(original_member)
                                overwrites.read_messages = False
                                overwrites.send_messages = False
                                await interaction.channel.set_permissions(original_member, overwrite=overwrites)
                                print(f"🔄 TICKETS: Permissões de {original_member.name} removidas em {interaction.channel.name} (carregado).")

                            resolved_category = discord.utils.get(interaction.guild.categories, id=RESOLVED_TICKET_CATEGORY_ID)
                            if resolved_category:
                                await interaction.channel.edit(category=resolved_category)
                                print(f"✅ TICKETS: Ticket {interaction.channel.name} movido para \'Tickets Resolvidos\' (carregado).")

                            conn_update_loaded = get_db_connection()
                            if conn_update_loaded:
                                cursor_update_loaded = conn_update_loaded.cursor()
                                try:
                                    cursor_update_loaded.execute("UPDATE tickets SET status = 'resolved' WHERE channel_id = %s", (channel_id_callback,))
                                    conn_update_loaded.commit()
                                    print(f"✅ DB: Status do ticket {channel_id_callback} atualizado para 'resolved' (carregado).")
                                except mysql.connector.Error as err:
                                    print(f"❌ ERRO DB: Falha ao atualizar status do ticket {channel_id_callback} para 'resolved' (carregado): {err}")
                                finally:
                                    if cursor_update_loaded:
                                        try:
                                            if cursor_update_loaded.with_rows: cursor_update_loaded.fetchall()
                                            cursor_update_loaded.close()
                                        except mysql.connector.Error as close_err:
                                            print(f"⚠️ DB Cleanup: Erro ao fechar cursor_update_loaded: {close_err}")
                                    if conn_update_loaded:
                                        try:
                                            conn_update_loaded.close()
                                        except mysql.connector.Error as close_err:
                                            print(f"⚠️ DB Cleanup: Erro ao fechar conn_update_loaded: {close_err}")
                            else:
                                print("❌ TICKETS: Falha ao obter conexão com o DB para atualizar status (carregado).")

                            await interaction.channel.send(MENSAGEM_TICKET_FECHADO.format(usuario=interaction.user.mention))

                            new_delete_button = discord.ui.Button(label="Excluir Ticket", style=discord.ButtonStyle.red, custom_id=f"delete_ticket_{channel_id_callback}")
                            # O callback precisa ser re-atribuído com o status atualizado
                            new_delete_button.callback = lambda inter: action_button_callback_loaded(inter, original_user_id=original_user_id, current_status="resolved", loaded_ticket_id=loaded_ticket_id)
                            new_view = discord.ui.View(timeout=None)
                            new_view.add_item(new_delete_button)

                            try:
                                # Tenta encontrar a última mensagem do bot que contém o botão
                                bot_message_with_view = None
                                async for msg in interaction.channel.history(limit=5):
                                    if msg.author == interaction.client.user and msg.components:
                                        for component_row in msg.components:
                                            for component in component_row.children:
                                                if isinstance(component, discord.ui.Button) and component.custom_id in [f"close_ticket_{channel_id_callback}", f"delete_ticket_{channel_id_callback}"]:
                                                    bot_message_with_view = msg
                                                    break
                                            if bot_message_with_view:
                                                break
                                        if bot_message_with_view:
                                            break

                                if bot_message_with_view:
                                    await bot_message_with_view.edit(view=new_view)
                                    self.bot.add_view(new_view, message_id=bot_message_with_view.id)
                                    print(f"✅ TICKETS: Botão em {bot_message_with_view.id} atualizado para 'Excluir Ticket' (carregado).")
                                else:
                                    await interaction.channel.send("O ticket foi resolvido. Clique no botão abaixo para excluí-lo definitivamente.", view=new_view)
                                    print(f"⚠️ TICKETS: Mensagem original do botão não encontrada (carregado). Nova mensagem com botão 'Excluir Ticket' enviada.")

                            except Exception as e:
                                print(f"❌ TICKETS: ERRO ao atualizar a mensagem do botão (carregado): {e}")
                                await interaction.channel.send("O ticket foi resolvido, mas houve um erro ao atualizar o botão. Clique no botão abaixo para excluí-lo definitivamente.", view=new_view)

                        except Exception as e:
                            await interaction.followup.send(f"Ocorreu um erro ao fechar o ticket: {str(e)}", ephemeral=True)
                            print(f"❌ TICKETS: ERRO ao fechar ticket {interaction.channel.name} (carregado): {str(e)}")

                    elif actual_status == "resolved":
                        # Lógica de Excluir Ticket (segundo clique)
                        try:
                            await interaction.channel.send(MENSAGEM_CONFIRMACAO_EXCLUSAO.format(usuario=interaction.user.mention))
                            print(f"🔄 TICKETS: Confirmação de exclusão para {interaction.channel.name} (carregado). Deletando canal.")
                            await asyncio.sleep(5)

                            # Remover ticket do banco de dados ANTES de deletar o canal
                            conn_delete = get_db_connection()
                            if conn_delete:
                                cursor_delete = conn_delete.cursor()
                                try:
                                    # Deleta usando o channel_id
                                    cursor_delete.execute("DELETE FROM tickets WHERE channel_id = %s", (channel_id_callback,))
                                    conn_delete.commit()
                                    print(f"✅ DB: Ticket {channel_id_callback} DELETADO do DB (final).")
                                except mysql.connector.Error as err:
                                    print(f"❌ ERRO DB: Falha ao deletar ticket {channel_id_callback} do DB (final): {err}")
                                    await interaction.followup.send(f"Erro ao remover o ticket do banco de dados. Por favor, remova-o manualmente se necessário.", ephemeral=True)
                                finally:
                                    if cursor_delete:
                                        try:
                                            if cursor_delete.with_rows: cursor_delete.fetchall()
                                            cursor_delete.close()
                                        except mysql.connector.Error as close_err:
                                            print(f"⚠️ DB Cleanup: Erro ao fechar cursor_delete: {close_err}")
                                    if conn_delete:
                                        try:
                                            conn_delete.close()
                                        except mysql.connector.Error as close_err:
                                            print(f"⚠️ DB Cleanup: Erro ao fechar conn_delete: {close_err}")
                            else:
                                print("❌ TICKETS: Falha ao obter conexão com o DB para deletar ticket.")
                                await interaction.followup.send("Não foi possível conectar ao banco de dados para remover o ticket. Por favor, remova-o manualmente se necessário.", ephemeral=True)

                            await interaction.channel.delete(reason="Ticket excluído por solicitação do usuário/moderação.")
                            print(f"✅ TICKETS: Canal {interaction.channel.name} deletado do Discord.")

                        except discord.Forbidden:
                            await interaction.followup.send("Não tenho permissão para deletar este canal. Por favor, remova-o manualmente.", ephemeral=True)
                            print(f"❌ TICKETS: Permissão negada para deletar canal {interaction.channel.name}.")
                        except Exception as e:
                            await interaction.followup.send(f"Ocorreu um erro ao excluir o ticket: {str(e)}", ephemeral=True)
                            print(f"❌ TICKETS: ERRO ao excluir ticket {interaction.channel.name}: {str(e)}")
                    else:
                        await interaction.followup.send("Este ticket está em um estado desconhecido. Por favor, contate um administrador.", ephemeral=True)
                        print(f"⚠️ TICKETS: Ticket {channel_id_callback} em estado desconhecido: {actual_status}.")

                # Atribui o callback correto ao botão com base no status carregado
                action_button.callback = lambda inter: action_button_callback_loaded(inter, original_user_id=user_id, current_status=status, loaded_ticket_id=ticket_id)

                action_view = discord.ui.View(timeout=None)
                action_view.add_item(action_button)
                self.bot.add_view(action_view)

                print(f"✅ SETUP_COG: Ticket {channel.name} ({channel_id}) carregado do DB com status '{status}' e botão reativado.")
            else:
                print(f"⚠️ SETUP_COG: Canal {channel_id} do ticket não encontrado no Discord. Removendo-o do DB para evitar dados inconsistentes.")
                conn_delete_orphan = get_db_connection()
                if conn_delete_orphan:
                    cursor_delete_orphan = conn_delete_orphan.cursor()
                    try:
                        cursor_delete_orphan.execute("DELETE FROM tickets WHERE channel_id = %s", (channel_id,))
                        conn_delete_orphan.commit()
                        print(f"✅ DB: Ticket órfão {channel_id} DELETADO do DB.")
                    except mysql.connector.Error as err:
                        print(f"❌ ERRO DB: Falha ao deletar ticket órfão {channel_id} do DB: {err}")
                    finally:
                        if cursor_delete_orphan:
                            try:
                                if cursor_delete_orphan.with_rows: cursor_delete_orphan.fetchall()
                                cursor_delete_orphan.close()
                            except mysql.connector.Error as close_err:
                                print(f"⚠️ DB Cleanup: Erro ao fechar cursor_delete_orphan: {close_err}")
                        if conn_delete_orphan:
                            try:
                                conn_delete_orphan.close()
                            except mysql.connector.Error as close_err:
                                print(f"⚠️ DB Cleanup: Erro ao fechar conn_delete_orphan: {close_err}")
                else:
                    print("❌ TICKETS: Falha ao obter conexão com o DB para deletar ticket órfão.")


# Função de setup para carregar a cog
async def setup(bot):
    cog = Tickets(bot)
    await bot.add_cog(cog)
    bot.once_ready_tasks.append(cog.setup_ticket_message)
    bot.once_ready_tasks.append(cog.load_tickets_from_db)
