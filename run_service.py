#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para executar o Reddit to Telegram Bot como serviço
Inclui funcionalidades de restart automático e gerenciamento de erros
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime
from reddit_to_telegram import RedditToTelegramBot

# Configuração de encoding UTF-8 para Windows
if sys.platform == 'win32':
    import os
    # Configura variáveis de ambiente para UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Tenta configurar o console para UTF-8 se possível
    try:
        import locale
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        pass

# Configuração de logging para o serviço
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RedditTelegramService')

class RedditTelegramService:
    def __init__(self):
        self.bot = None
        self.running = True
        self.restart_count = 0
        self.max_restarts = 10
        self.restart_delay = 60  # segundos
        
        # Configura handlers para sinais do sistema
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handler para sinais do sistema (Ctrl+C, etc.)"""
        logger.info(f"Sinal {signum} recebido. Parando o serviço...")
        self.running = False
    
    def initialize_bot(self):
        """Inicializa o bot com tratamento de erros"""
        try:
            self.bot = RedditToTelegramBot()
            logger.info("Bot inicializado com sucesso")
            return True
        except FileNotFoundError:
            logger.error("Arquivo config.json não encontrado")
            logger.error("Execute 'python setup_and_test.py' primeiro")
            return False
        except Exception as e:
            logger.error(f"Erro ao inicializar bot: {e}")
            return False
    
    def run_bot_cycle(self):
        """Executa um ciclo do bot com tratamento de erros"""
        try:
            if not self.bot:
                if not self.initialize_bot():
                    return False
            
            # Executa uma verificação
            self.bot.check_subreddits()
            self.bot.save_processed_posts()
            
            # Aguarda o intervalo configurado
            interval = self.bot.config.get('check_interval', 300)
            logger.info(f"Ciclo concluído. Aguardando {interval} segundos...")
            
            # Aguarda com verificação periódica do status
            for _ in range(interval):
                if not self.running:
                    break
                time.sleep(1)
            
            return True
            
        except KeyboardInterrupt:
            logger.info("Interrupção pelo usuário")
            self.running = False
            return False
        except UnicodeEncodeError as e:
            logger.error(f"Erro de codificação Unicode: {e}")
            return True  # Continua executando apesar do erro de encoding
        except Exception as e:
            logger.error(f"Erro no ciclo do bot: {e}")
            return False
    
    def run(self):
        """Executa o serviço com restart automático"""
        logger.info("=" * 50)
        logger.info("Reddit to Telegram Service iniciado")
        logger.info(f"Hora de início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        logger.info(f"PID: {os.getpid()}")
        logger.info(f"Python: {sys.version.split()[0]}")
        logger.info(f"Plataforma: {sys.platform}")
        logger.info(f"Encoding: UTF-8 configurado")
        logger.info(f"Max restarts: {self.max_restarts}")
        logger.info(f"Restart delay: {self.restart_delay}s")
        logger.info("=" * 50)
        
        while self.running and self.restart_count < self.max_restarts:
            try:
                # Inicializa o bot se necessário
                if not self.bot:
                    if not self.initialize_bot():
                        logger.error("Falha na inicialização. Tentando novamente em 30 segundos...")
                        time.sleep(30)
                        continue
                
                # Executa o bot
                logger.info("Iniciando monitoramento...")
                while self.running:
                    if not self.run_bot_cycle():
                        break
                
                # Se chegou aqui, o bot parou por algum motivo
                if self.running:
                    self.restart_count += 1
                    logger.warning(f"Bot parou inesperadamente. Restart {self.restart_count}/{self.max_restarts}")
                    
                    if self.restart_count < self.max_restarts:
                        logger.info(f"Reiniciando em {self.restart_delay} segundos...")
                        time.sleep(self.restart_delay)
                        self.bot = None  # Força reinicialização
                    else:
                        logger.error("Número máximo de restarts atingido. Parando o serviço.")
                        break
                
            except UnicodeEncodeError as e:
                logger.error(f"Erro de codificação Unicode no serviço: {e}")
                # Não conta como restart para erros de encoding
                continue
            except Exception as e:
                logger.error(f"Erro crítico no serviço: {e}")
                self.restart_count += 1
                
                if self.restart_count < self.max_restarts:
                    logger.info(f"Tentando restart em {self.restart_delay} segundos...")
                    time.sleep(self.restart_delay)
                    self.bot = None
                else:
                    logger.error("Muitos erros consecutivos. Parando o serviço.")
                    break
        
        # Salva posts processados e mensagens falhadas antes de finalizar
        if self.bot:
            try:
                self.bot.save_processed_posts()
                self.bot.save_failed_messages()
                logger.info("Posts processados e mensagens falhadas salvos com sucesso")
            except Exception as e:
                logger.error(f"Erro ao salvar posts processados e mensagens falhadas: {e}")
        
        logger.info("Serviço finalizado")
        logger.info(f"Total de restarts: {self.restart_count}")
        logger.info(f"Hora de término: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

def show_status():
    """Mostra informações de status do serviço"""
    print("Reddit to Telegram Service - Status")
    print("=" * 40)
    
    # Verifica se o arquivo de configuração existe
    if os.path.exists('config.json'):
        print("✅ Arquivo de configuração: OK")
    else:
        print("❌ Arquivo de configuração: NÃO ENCONTRADO")
        print("   Execute: python setup_and_test.py")
    
    # Verifica logs recentes
    if os.path.exists('service.log'):
        print("✅ Arquivo de log: OK")
        try:
            with open('service.log', 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    print(f"   Última entrada: {lines[-1].strip()}")
                    print(f"   Total de linhas: {len(lines)}")
        except Exception as e:
            print(f"   Erro ao ler log: {e}")
    else:
        print("⚠️  Arquivo de log: NÃO ENCONTRADO")
    
    # Verifica posts processados
    if os.path.exists('processed_posts.json'):
        print("✅ Histórico de posts: OK")
        try:
            import json
            with open('processed_posts.json', 'r', encoding='utf-8') as f:
                posts = json.load(f)
                print(f"   Posts processados: {len(posts)}")
        except Exception as e:
            print(f"   Erro ao ler histórico: {e}")
    else:
        print("⚠️  Histórico de posts: NÃO ENCONTRADO")
    
    # Verifica mensagens falhadas
    if os.path.exists('failed_messages.json'):
        try:
            import json
            with open('failed_messages.json', 'r', encoding='utf-8') as f:
                failed_messages = json.load(f)
                print(f"⚠️ Mensagens falhadas pendentes: {len(failed_messages)}")
                if failed_messages:
                    for i, msg in enumerate(failed_messages[:3]):  # Mostra apenas as 3 primeiras
                        print(f"   {i+1}. Tentativas: {msg.get('retry_count', 0)}/3 - {msg.get('timestamp', 'N/A')}")
                    if len(failed_messages) > 3:
                        print(f"   ... e mais {len(failed_messages) - 3} mensagens")
        except Exception as e:
            print(f"❌ Erro ao ler mensagens falhadas: {e}")
    else:
        print("✅ Nenhuma mensagem falhada pendente")
    
    # Verifica log do bot principal
    if os.path.exists('reddit_bot.log'):
        print("✅ Log do bot: OK")
        try:
            with open('reddit_bot.log', 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    print(f"   Última atividade: {lines[-1].strip()}")
        except Exception as e:
            print(f"   Erro ao ler log do bot: {e}")
    else:
        print("⚠️  Log do bot: NÃO ENCONTRADO")

def main():
    """Função principal"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status':
            show_status()
            return
        elif command == 'help':
            print("Reddit to Telegram Service")
            print("Uso: python run_service.py [comando]")
            print()
            print("Comandos disponíveis:")
            print("  (nenhum)  - Executa o serviço")
            print("  status    - Mostra status do serviço")
            print("  help      - Mostra esta ajuda")
            return
        else:
            print(f"Comando desconhecido: {command}")
            print("Use 'python run_service.py help' para ver os comandos disponíveis")
            return
    
    # Executa o serviço
    try:
        service = RedditTelegramService()
        service.run()
    except Exception as e:
        logger.error(f"Erro fatal no serviço: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())