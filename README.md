### 📖 Descrição do Projeto

Este repositório reúne uma coleção de **cogs para bots de Discord desenvolvidos em Python**, prontas para uso e totalmente configuráveis. Cada cog possui **suas respectivas configurações comentadas dentro do arquivo**, tornando **fácil o acesso, a compreensão e a modificação** de cada parâmetro.

💡 Com este projeto você poderá:

* Adicionar funcionalidades ao seu bot de forma rápida e modular.  
* Personalizar comandos e eventos com configurações simples e comentadas diretamente nos arquivos.  
* Aprender a criar suas próprias cogs a partir de exemplos claros e bem estruturados.  
* Reaproveitar código pronto, economizando tempo no desenvolvimento.  

🚀 Ideal para quem deseja:

* Montar bots de Discord mais completos.  
* Usar soluções prontas, mas flexíveis e facilmente configuráveis.  
* Estudar a estrutura de cogs no `discord.py` para evoluir no desenvolvimento.

## 🛠️ Cogs Disponíveis

### 🎁 **Sorteios** (`sorteios.py`)
Sistema completo de sorteios com comando `/sorteio` e botões interativos. Suporta múltiplos ganhadores, requisito de convites, agendamento automático e persistência após reinicialização do bot. Integração com MySQL para armazenamento e sistema de fallback para sorteios perdidos.

**Funcionalidades:** Interface com embeds coloridos, seleção aleatória de vencedores, views persistentes, sistema de permissões flexível e configurações totalmente personalizáveis.

### 🎫 **Sistema de Tickets** (`tickets.py`)
Sistema completo de atendimento ao cliente através de tickets privados. Permite abertura de canais individuais organizados por categorias, com controle de permissões por cargos, estados de ticket (aberto/resolvido/excluído) e integração com banco MySQL.

**Funcionalidades:** Interface com dropdown de categorias (Geral, Denúncias, Financeiro, Outros), botões persistentes para fechar/excluir tickets, sistema de numeração sequencial, movimentação automática entre categorias, controle de permissões granular e configuração via comando `/setup`. Suporta reativação automática de tickets após reinicialização do bot.
