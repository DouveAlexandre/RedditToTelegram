#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de configuração e teste para o Reddit to Telegram Bot
Ajuda a configurar e testar as credenciais antes de executar o bot principal
"""

import json
import praw
import requests
from datetime import datetime

def create_config():
    """Cria arquivo de configuração interativamente"""
    print("=== Configuração do Reddit to Telegram Bot ===")
    print()
    
    # Configurações do Reddit
    print("1. Configurações do Reddit:")
    reddit_client_id = input("Client ID do Reddit: ").strip()
    reddit_client_secret = input("Client Secret do Reddit: ").strip()
    reddit_user_agent = input("User Agent (ex: RedditToTelegram/1.0 by SeuUsername): ").strip()
    
    print()
    
    # Configurações do Telegram
    print("2. Configurações do Telegram:")
    telegram_bot_token = input("Token do Bot do Telegram: ").strip()
    telegram_chat_id = input("Chat ID do Telegram: ").strip()
    bot_link = input("Link do seu bot/canal (ex: https://t.me/seu_bot): ").strip() or "https://t.me/seu_bot_aqui"
    
    print()
    
    # Subreddits
    print("3. Subreddits para monitorar:")
    print("Digite os nomes dos subreddits (sem 'r/'), separados por vírgula:")
    subreddits_input = input("Subreddits (ex: python,programming,technology): ").strip()
    subreddits = [s.strip() for s in subreddits_input.split(',') if s.strip()]
    
    print()
    
    # Configurações avançadas
    print("4. Configurações avançadas:")
    try:
        check_interval = int(input("Intervalo entre verificações em segundos (padrão 300): ") or "300")
    except ValueError:
        check_interval = 300
    
    try:
        max_posts = int(input("Máximo de posts por verificação (padrão 10): ") or "10")
    except ValueError:
        max_posts = 10
    
    debug_emoji_input = input("Ativar emoji de depuração nas mensagens? (S/n): ").strip().lower()
    debug_emoji = debug_emoji_input not in ['n', 'no', 'não', 'nao']
    
    # Cria o dicionário de configuração
    config = {
        "reddit": {
            "client_id": reddit_client_id,
            "client_secret": reddit_client_secret,
            "user_agent": reddit_user_agent
        },
        "telegram": {
            "bot_token": telegram_bot_token,
            "chat_id": telegram_chat_id
        },
        "bot_link": bot_link,
        "subreddits": subreddits,
        "check_interval": check_interval,
        "max_posts_per_check": max_posts,
        "debug_emoji": debug_emoji
    }
    
    # Salva o arquivo
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print("\n✅ Arquivo config.json criado com sucesso!")
    return config

def test_reddit_connection(config):
    """Testa a conexão com o Reddit"""
    print("\n=== Testando conexão com Reddit ===")
    
    try:
        reddit = praw.Reddit(
            client_id=config['reddit']['client_id'],
            client_secret=config['reddit']['client_secret'],
            user_agent=config['reddit']['user_agent']
        )
        
        # Testa acessando um subreddit
        test_subreddit = reddit.subreddit('python')
        posts = list(test_subreddit.hot(limit=1))
        
        if posts:
            print(f"✅ Conexão com Reddit OK!")
            print(f"   Teste realizado com r/python")
            print(f"   Post de teste: {posts[0].title[:50]}...")
            return True
        else:
            print("❌ Não foi possível obter posts do Reddit")
            return False
            
    except Exception as e:
        print(f"❌ Erro na conexão com Reddit: {e}")
        return False

def test_telegram_connection(config):
    """Testa a conexão com o Telegram"""
    print("\n=== Testando conexão com Telegram ===")
    
    try:
        bot_token = config['telegram']['bot_token']
        chat_id = config['telegram']['chat_id']
        
        # Testa enviando uma mensagem
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        test_message = f"🤖 Teste de conexão - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        data = {
            'chat_id': chat_id,
            'text': test_message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if result.get('ok'):
            print("✅ Conexão com Telegram OK!")
            print(f"   Mensagem de teste enviada com sucesso")
            print(f"   Message ID: {result['result']['message_id']}")
            return True
        else:
            print(f"❌ Erro na resposta do Telegram: {result}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão com Telegram: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado no Telegram: {e}")
        return False

def test_subreddits(config):
    """Testa o acesso aos subreddits configurados"""
    print("\n=== Testando acesso aos subreddits ===")
    
    try:
        reddit = praw.Reddit(
            client_id=config['reddit']['client_id'],
            client_secret=config['reddit']['client_secret'],
            user_agent=config['reddit']['user_agent']
        )
        
        all_ok = True
        for subreddit_name in config['subreddits']:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                posts = list(subreddit.new(limit=1))
                
                if posts:
                    print(f"✅ r/{subreddit_name} - OK ({posts[0].title[:30]}...)")
                else:
                    print(f"⚠️  r/{subreddit_name} - Sem posts recentes")
                    
            except Exception as e:
                print(f"❌ r/{subreddit_name} - Erro: {e}")
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        print(f"❌ Erro geral ao testar subreddits: {e}")
        return False

def main():
    """Função principal do script de configuração"""
    print("Reddit to Telegram Bot - Setup e Teste")
    print("=" * 40)
    
    # Verifica se já existe config.json
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("📁 Arquivo config.json encontrado!")
        
        choice = input("\nDeseja recriar a configuração? (s/N): ").strip().lower()
        if choice in ['s', 'sim', 'y', 'yes']:
            config = create_config()
    except FileNotFoundError:
        print("📁 Arquivo config.json não encontrado. Criando nova configuração...")
        config = create_config()
    
    # Executa os testes
    print("\n" + "=" * 40)
    print("Executando testes de conectividade...")
    
    reddit_ok = test_reddit_connection(config)
    telegram_ok = test_telegram_connection(config)
    subreddits_ok = test_subreddits(config)
    
    # Resumo final
    print("\n" + "=" * 40)
    print("RESUMO DOS TESTES:")
    print(f"Reddit: {'✅ OK' if reddit_ok else '❌ FALHOU'}")
    print(f"Telegram: {'✅ OK' if telegram_ok else '❌ FALHOU'}")
    print(f"Subreddits: {'✅ OK' if subreddits_ok else '❌ ALGUNS FALHARAM'}")
    
    if reddit_ok and telegram_ok:
        print("\n🎉 Configuração concluída com sucesso!")
        print("Agora você pode executar: python reddit_to_telegram.py")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique as configurações.")
        print("Edite o arquivo config.json e execute este script novamente.")

if __name__ == "__main__":
    main()