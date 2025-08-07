# Reddit to Telegram Bot

Script Python que monitora postagens em comunidades específicas do Reddit e envia notificações formatadas para um grupo do Telegram.

## Funcionalidades

- ✅ Monitora múltiplos subreddits simultaneamente
- ✅ Detecta automaticamente novos posts
- ✅ Formata mensagens com título, descrição, autor, estatísticas
- ✅ Envia mídia (imagens) diretamente no Telegram
- ✅ Download e envio automático de vídeos do Reddit
- ✅ Emojis de depuração para identificar tipo de conteúdo
- ✅ Evita posts duplicados
- ✅ Log detalhado de atividades
- ✅ Configuração via arquivo JSON

## Pré-requisitos

### 1. Credenciais do Reddit

1. Acesse [Reddit Apps](https://www.reddit.com/prefs/apps)
2. Clique em "Create App" ou "Create Another App"
3. Escolha "script" como tipo de aplicação
4. Anote o `client_id` (abaixo do nome da app) e `client_secret`

### 2. Bot do Telegram

1. Converse com [@BotFather](https://t.me/botfather) no Telegram
2. Use o comando `/newbot` e siga as instruções
3. Anote o token do bot fornecido
4. Para obter o Chat ID do grupo:
   - Adicione o bot ao grupo
   - Envie uma mensagem no grupo
   - Acesse: `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
   - Procure pelo `chat.id` na resposta

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd IFTTT
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Execute o script pela primeira vez para gerar o arquivo de configuração:
```bash
python reddit_to_telegram.py
```

4. Edite o arquivo `config.json` criado com suas credenciais:
```json
{
    "reddit": {
        "client_id": "seu_client_id_aqui",
        "client_secret": "seu_client_secret_aqui",
        "user_agent": "RedditToTelegram/1.0 by SeuUsername"
    },
    "telegram": {
        "bot_token": "seu_bot_token_aqui",
        "chat_id": "seu_chat_id_aqui"
    },
    "bot_link": "https://t.me/seu_canal_vip",
    "subreddits": [
        "python",
        "programming",
        "technology"
    ],
    "check_interval": 300,
    "max_posts_per_check": 10
}
```

## Configuração

### Parâmetros do config.json

- **reddit.client_id**: ID da aplicação Reddit
- **reddit.client_secret**: Secret da aplicação Reddit
- **reddit.user_agent**: Identificação do seu bot (formato: "NomeApp/Versão by Username")
- **telegram.bot_token**: Token do bot do Telegram
- **telegram.chat_id**: ID do chat/grupo onde enviar mensagens
- **subreddits**: Lista de subreddits para monitorar (sem o "r/")
- **check_interval**: Intervalo entre verificações em segundos (padrão: 300 = 5 minutos)
- **max_posts_per_check**: Máximo de posts para verificar por ciclo
- **debug_emoji**: Ativar/desativar emojis de depuração nas mensagens (true/false, padrão: true)

## Uso

1. Execute o bot:
```bash
python reddit_to_telegram.py
```

2. O bot irá:
   - Verificar os subreddits configurados
   - Detectar novos posts
   - Enviar notificações formatadas para o Telegram
   - Aguardar o intervalo configurado antes da próxima verificação

3. Para parar o bot, use `Ctrl+C`

##### Formato das Mensagens

As mensagens enviadas para o Telegram seguem este formato:

**Com nome da modelo identificado:**
```
[Emoji de Depuração] 🔥 *[Nome da Modelo]* • *COMPLETO NO VIP* 🔥

💎 Quer acessar o melhor conteúdo exclusivo?
🎯 *Conteúdo Premium*: Curadoria especial para membros que buscam qualidade e variedade!

🚀 *VIP COMPLETO* - [CLIQUE AQUI](link_do_bot) 🚀
```

**Sem nome da modelo identificado:**
```
[Emoji de Depuração] 🔥 *COMPLETO NO VIP* 🔥

💎 Quer acessar o melhor conteúdo exclusivo?
🎯 *Conteúdo Premium*: Curadoria especial para membros que buscam qualidade e variedade!

🚀 *VIP COMPLETO* - [CLIQUE AQUI](link_do_bot) 🚀
```

### Emojis de Depuração:
Os emojis de depuração ajudam a identificar o tipo de conteúdo e podem ser ativados/desativados através da configuração `debug_emoji`:
- 📝 **Texto**: Posts apenas com texto
- 🖼️ **Imagem**: Posts com imagens
- 🎥 **Vídeo Reddit**: Vídeos hospedados no Reddit (baixados e enviados)
- 📹 **Vídeo Genérico**: Outros tipos de vídeo
- 🎬 **YouTube**: Links do YouTube
- 🔗 **Link**: Links genéricos

**Nota**: Para desativar os emojis de depuração, defina `"debug_emoji": false` no arquivo `config.json`.

### Processamento de Mídia:
- **Imagens**: Enviadas diretamente como foto no Telegram
- **Vídeos do Reddit**: Baixados automaticamente e enviados como vídeo nativo
- **Links**: Incluídos na mensagem com preview automático
- **Posts de texto**: Apenas título e conteúdo

### Configuração do Link do Bot:
Para personalizar o link "CLIQUE AQUI" nas mensagens:
1. Adicione o campo `"bot_link"` no seu arquivo `config.json`
2. Exemplo: `"bot_link": "https://t.me/seu_canal_vip"`
3. O link pode ser do seu bot, canal, grupo, site, etc.
4. Se não configurado, usará o valor padrão `https://t.me/seu_bot_aqui`
5. O link aparecerá oculto no texto "CLIQUE AQUI" usando formatação Markdown



## Arquivos Gerados

- `config.json`: Configurações do bot
- `processed_posts.json`: IDs dos posts já processados (evita duplicatas)
- `reddit_telegram_bot.log`: Log de atividades do bot

## Solução de Problemas

### Erro de autenticação Reddit
- Verifique se o `client_id` e `client_secret` estão corretos
- Certifique-se de que o `user_agent` está no formato correto

### Mensagens não chegam no Telegram
- Verifique se o `bot_token` está correto
- Confirme se o `chat_id` está correto
- Certifique-se de que o bot foi adicionado ao grupo

### Bot não encontra posts novos
- Verifique se os nomes dos subreddits estão corretos
- Alguns subreddits podem ter poucos posts novos
- Ajuste o `check_interval` se necessário

## Limitações

- O Reddit tem limites de taxa para APIs
- O Telegram tem limites de mensagens por segundo
- Posts muito antigos não serão detectados na primeira execução

## Contribuição

Sinta-se à vontade para contribuir com melhorias, correções de bugs ou novas funcionalidades!