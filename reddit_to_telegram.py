#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para monitorar postagens do Reddit e enviar para Telegram
Detecta novas postagens em subreddits específicos e envia formatadas para um grupo do Telegram
"""

import praw
import requests
import time
import json
import os
import sys
import tempfile
import urllib.parse
from datetime import datetime
from typing import List, Dict, Set, Optional
import logging
import re

# Configuração de logging com suporte a UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reddit_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

class RedditToTelegramBot:
    def __init__(self, config_file='config.json'):
        """Inicializa o bot com configurações do arquivo JSON"""
        self.config = self.load_config(config_file)
        self.reddit = self.setup_reddit()
        self.processed_posts = self.load_processed_posts()
        self.failed_messages = self.load_failed_messages()
        
    def load_config(self, config_file: str) -> Dict:
        """Carrega configurações do arquivo JSON"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Arquivo de configuração {config_file} não encontrado")
            self.create_sample_config(config_file)
            raise
        except json.JSONDecodeError:
            logger.error(f"Erro ao decodificar JSON do arquivo {config_file}")
            raise
    
    def create_sample_config(self, config_file: str):
        """Cria um arquivo de configuração de exemplo"""
        sample_config = {
            "reddit": {
                "client_id": "SEU_CLIENT_ID_REDDIT",
                "client_secret": "SEU_CLIENT_SECRET_REDDIT",
                "user_agent": "RedditToTelegram/1.0 by YourUsername"
            },
            "telegram": {
                "bot_token": "SEU_BOT_TOKEN_TELEGRAM",
                "chat_id": "SEU_CHAT_ID_TELEGRAM"
            },
            "subreddits": [
                "python",
                "programming",
                "technology"
            ],
            "check_interval": 300,
            "max_posts_per_check": 10,
            "debug_emoji": true,
            "send_text_only_posts": false
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Arquivo de configuração de exemplo criado: {config_file}")
        logger.info("Por favor, edite o arquivo com suas credenciais antes de executar novamente")
    
    def setup_reddit(self) -> praw.Reddit:
        """Configura a conexão com a API do Reddit"""
        try:
            reddit = praw.Reddit(
                client_id=self.config['reddit']['client_id'],
                client_secret=self.config['reddit']['client_secret'],
                user_agent=self.config['reddit']['user_agent']
            )
            # Testa a conexão
            reddit.user.me()
            logger.info("Conexão com Reddit estabelecida com sucesso")
            return reddit
        except Exception as e:
            logger.error(f"Erro ao conectar com Reddit: {e}")
            raise
    
    def load_processed_posts(self) -> Set[str]:
        """Carrega IDs de posts já processados"""
        try:
            with open('processed_posts.json', 'r') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()
    
    def save_processed_posts(self):
        """Salva IDs de posts processados"""
        with open('processed_posts.json', 'w') as f:
            json.dump(list(self.processed_posts), f)
    
    def load_failed_messages(self) -> List[Dict]:
        """Carrega mensagens que falharam no envio"""
        try:
            if os.path.exists('failed_messages.json'):
                with open('failed_messages.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar mensagens falhadas: {e}")
        return []
    
    def save_failed_messages(self):
        """Salva mensagens que falharam no envio"""
        try:
            with open('failed_messages.json', 'w', encoding='utf-8') as f:
                json.dump(self.failed_messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar mensagens falhadas: {e}")
    
    def add_failed_message(self, message: str, media_url: str = None, post_url: str = None):
        """Adiciona uma mensagem à lista de falhadas"""
        failed_msg = {
            'message': message,
            'media_url': media_url,
            'post_url': post_url,
            'timestamp': datetime.now().isoformat(),
            'retry_count': 0
        }
        self.failed_messages.append(failed_msg)
        self.save_failed_messages()
        logger.info(f"Mensagem adicionada à lista de falhadas: {len(self.failed_messages)} total")
    
    def retry_failed_messages(self):
        """Tenta reenviar mensagens falhadas como texto simples"""
        if not self.failed_messages:
            return
        
        logger.info(f"Tentando reenviar {len(self.failed_messages)} mensagens falhadas...")
        messages_to_remove = []
        
        for i, failed_msg in enumerate(self.failed_messages):
            try:
                # Cria mensagem de texto com link se disponível
                text_message = failed_msg['message']
                if failed_msg.get('post_url'):
                    text_message += f"\n\n🔗 [Ver post original]({failed_msg['post_url']})"
                
                # Tenta enviar como texto simples
                if self.send_text_message(text_message):
                    messages_to_remove.append(i)
                    logger.info(f"Mensagem falhada reenviada com sucesso")
                else:
                    failed_msg['retry_count'] += 1
                    if failed_msg['retry_count'] >= 3:
                        messages_to_remove.append(i)
                        logger.warning(f"Mensagem descartada após 3 tentativas")
                
            except Exception as e:
                logger.error(f"Erro ao reenviar mensagem falhada: {e}")
                failed_msg['retry_count'] += 1
                if failed_msg['retry_count'] >= 3:
                    messages_to_remove.append(i)
        
        # Remove mensagens processadas (em ordem reversa para não afetar índices)
        for i in reversed(messages_to_remove):
            self.failed_messages.pop(i)
        
        if messages_to_remove:
            self.save_failed_messages()
            logger.info(f"Removidas {len(messages_to_remove)} mensagens da lista de falhadas")
    
    def send_text_message(self, message: str) -> bool:
        """Envia apenas mensagem de texto para o Telegram"""
        bot_token = self.config['telegram']['bot_token']
        chat_id = self.config['telegram']['chat_id']
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de texto: {e}")
            return False
    

    
    def download_reddit_image(self, post) -> Optional[str]:
        """Baixa imagem do Reddit e retorna a URL da melhor qualidade"""
        try:
            image_url = None
            
            # Método 1: Verifica media_metadata para imagens (apenas a primeira)
            if hasattr(post, 'media_metadata') and post.media_metadata:
                logger.info(f"Verificando media_metadata para imagens (apenas primeira)")
                # Ordena as chaves para garantir consistência na ordem
                sorted_media_ids = sorted(post.media_metadata.keys())
                for media_id in sorted_media_ids:
                    media_info = post.media_metadata[media_id]
                    if media_info.get('e') == 'Image':
                        # Prioriza a imagem de melhor qualidade (campo 's')
                        if 's' in media_info and 'u' in media_info['s']:
                            image_url = media_info['s']['u']
                            logger.info(f"URL da primeira imagem encontrada via media_metadata (melhor qualidade): {image_url}")
                            break
                        # Fallback para o campo 'o' (original)
                        elif 'o' in media_info and len(media_info['o']) > 0 and 'u' in media_info['o'][0]:
                            image_url = media_info['o'][0]['u']
                            logger.info(f"URL da primeira imagem encontrada via media_metadata (original): {image_url}")
                            break
                        # Fallback para o maior preview disponível
                        elif 'p' in media_info and len(media_info['p']) > 0:
                            # Pega o maior preview disponível
                            largest_preview = max(media_info['p'], key=lambda x: x.get('x', 0) * x.get('y', 0))
                            if 'u' in largest_preview:
                                image_url = largest_preview['u']
                                logger.info(f"URL da primeira imagem encontrada via media_metadata (preview): {image_url}")
                                break
            
            # Método 2: Verifica se a URL do post é uma imagem direta
            if not image_url and not post.is_self:
                if any(ext in post.url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    image_url = post.url
                    logger.info(f"URL da imagem encontrada diretamente: {image_url}")
            
            # Método 3: Verifica preview para imagens (apenas a primeira)
            if not image_url and hasattr(post, 'preview') and post.preview:
                if 'images' in post.preview and len(post.preview['images']) > 0:
                    preview_image = post.preview['images'][0]  # Pega apenas a primeira imagem
                    if 'source' in preview_image and 'url' in preview_image['source']:
                        image_url = preview_image['source']['url']
                        logger.info(f"URL da primeira imagem encontrada no preview: {image_url}")
            
            if not image_url:
                logger.info(f"Nenhuma URL de imagem encontrada para o post {post.id}")
                return None
            
            # Limpa caracteres de escape HTML
            image_url = image_url.replace('&amp;', '&')
            
            return image_url
            
        except Exception as e:
            logger.error(f"Erro ao extrair URL da imagem do Reddit: {e}")
            return None
    
    def download_reddit_video(self, post) -> Optional[str]:
        """Baixa vídeo do Reddit e retorna o caminho do arquivo temporário"""
        try:
            video_url = None
            
            # Método 1: Vídeo direto do Reddit (is_video=True)
            if hasattr(post, 'is_video') and post.is_video:
                if hasattr(post, 'media') and post.media:
                    if 'reddit_video' in post.media:
                        video_url = post.media['reddit_video']['fallback_url']
                    elif 'oembed' in post.media:
                        video_url = post.media['oembed'].get('thumbnail_url')
                
                if not video_url and 'v.redd.it' in post.url:
                    video_url = post.url + '/DASH_720.mp4'
            
            # Método 2: Post de texto com vídeo incorporado (is_self=True)
            elif post.is_self and hasattr(post, 'media') and post.media:
                logger.info(f"Analisando post de texto com media: {post.media}")
                if 'reddit_video' in post.media:
                    video_url = post.media['reddit_video']['fallback_url']
                    logger.info(f"Vídeo encontrado em post de texto: {video_url}")
            
            # Método 3: Vídeo em media_metadata (posts NSFW com vídeo incorporado) - apenas o primeiro
            if not video_url and hasattr(post, 'media_metadata') and post.media_metadata:
                logger.info(f"Método 3: Verificando media_metadata (apenas primeiro vídeo)")
                # Ordena as chaves para garantir consistência na ordem
                sorted_media_ids = sorted(post.media_metadata.keys())
                for media_id in sorted_media_ids:
                    media_info = post.media_metadata[media_id]
                    if media_info.get('e') == 'RedditVideo':
                        # Prioriza HLS sobre DASH
                        if 'hlsUrl' in media_info:
                            video_url = media_info['hlsUrl']
                            logger.info(f"URL HLS do primeiro vídeo encontrada via media_metadata: {video_url}")
                            break
                        elif 'dashUrl' in media_info:
                            video_url = media_info['dashUrl']
                            logger.info(f"URL DASH do primeiro vídeo encontrada via media_metadata: {video_url}")
                            break
            
            # Método 4: Verifica se há preview com vídeo
            if not video_url and hasattr(post, 'preview') and post.preview:
                logger.info(f"Verificando preview para vídeo")
                if 'reddit_video_preview' in post.preview:
                    video_url = post.preview['reddit_video_preview']['fallback_url']
                    logger.info(f"Vídeo encontrado no preview: {video_url}")
            
            if not video_url:
                logger.info(f"Nenhuma URL de vídeo encontrada para o post {post.id}")
                return None
            
            # Para URLs HLS e DASH, mantém os parâmetros de query
            # Apenas remove parâmetros para URLs diretas de MP4
            if not any(format_type in video_url for format_type in ['HLSPlaylist.m3u8', 'DASHPlaylist.mpd']):
                video_url = video_url.split('?')[0]
            
            # Verifica se é HLS ou DASH que precisa de conversão
            if 'HLSPlaylist.m3u8' in video_url or 'DASHPlaylist.mpd' in video_url:
                logger.info(f"Detectado stream HLS/DASH, usando yt-dlp com URL do post: {post.url}")
                return self.convert_hls_to_mp4(post.url)
            else:
                # Baixa vídeo MP4 direto
                logger.info(f"Baixando vídeo MP4: {video_url}")
                response = requests.get(video_url, timeout=60, stream=True)
                response.raise_for_status()
                
                # Cria arquivo temporário
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                
                # Escreve o conteúdo do vídeo
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                
                temp_file.close()
                logger.info(f"Vídeo baixado: {temp_file.name}")
                return temp_file.name
            
        except Exception as e:
            logger.error(f"Erro ao baixar vídeo do Reddit: {e}")
            return None
    
    def convert_hls_to_mp4(self, reddit_url: str) -> Optional[str]:
        """Baixa vídeo do Reddit usando yt-dlp"""
        try:
            import subprocess
            
            # Cria arquivo temporário para o MP4 convertido
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_file.close()
            
            # Comando yt-dlp para baixar sem merge (evita necessidade do ffmpeg)
            cmd = [
                'yt-dlp',
                '--no-playlist',
                '--force-overwrites',
                '--output', temp_file.name.replace('.mp4', '.%(ext)s'),
                '--no-check-certificate',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--format', 'dash-4+dash-6/dash-3+dash-6/dash-2+dash-6/dash-1+dash-6/hls-1157-0/hls-768-0/hls-455-0/hls-297-0/best',  # Formatos específicos do Reddit
                '--no-post-overwrites',
                '--verbose',        # Mais informações para debug
                reddit_url
            ]
            
            logger.info(f"Baixando vídeo do Reddit com yt-dlp: {reddit_url}")
            
            try:
                # Executa yt-dlp
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=180  # 3 minutos timeout
                )
                
                if result.returncode == 0:
                    # Procura por arquivos baixados com qualquer extensão
                    base_name = temp_file.name.replace('.mp4', '')
                    possible_files = []
                    
                    # Verifica diretório para arquivos com o nome base
                    import glob
                    pattern = base_name + '.*'
                    possible_files = glob.glob(pattern)
                    
                    # Encontra o arquivo baixado
                    downloaded_file = None
                    for file_path in possible_files:
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            downloaded_file = file_path
                            break
                    
                    if downloaded_file:
                        logger.info(f"Download HLS/DASH concluído: {downloaded_file}")
                        return downloaded_file
                    else:
                        logger.warning(f"Nenhum arquivo válido encontrado após download")
                        return None
                else:
                    logger.warning(f"yt-dlp falhou - código: {result.returncode}")
                    logger.warning(f"stdout: {result.stdout}")
                    logger.warning(f"stderr: {result.stderr}")
                    
                    # Tenta listar formatos disponíveis para debug
                    try:
                        list_cmd = ['yt-dlp', '--list-formats', reddit_url]
                        list_result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
                        if list_result.returncode == 0:
                            logger.info(f"Formatos disponíveis para {reddit_url}:")
                            logger.info(list_result.stdout)
                    except Exception as e:
                        logger.warning(f"Erro ao listar formatos: {e}")
                    
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                    return None
                    
            except subprocess.TimeoutExpired:
                logger.warning("Timeout no download com yt-dlp")
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                return None
            except Exception as e:
                logger.warning(f"Erro no download com yt-dlp: {e}")
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                return None
                
        except FileNotFoundError:
            logger.error("yt-dlp não encontrado. Instale o yt-dlp para baixar vídeos HLS/DASH")
            return None
        except Exception as e:
            logger.error(f"Erro no download HLS/DASH: {e}")
            if 'temp_file' in locals() and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            return None
    
    def cleanup_temp_file(self, file_path: str):
        """Remove arquivo temporário"""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Arquivo temporário removido: {file_path}")
        except Exception as e:
            logger.error(f"Erro ao remover arquivo temporário {file_path}: {e}")
    
    def has_media_content(self, post) -> bool:
        """Verifica se o post contém mídia (imagem ou vídeo)"""
        try:
            # Verifica se é vídeo do Reddit
            if hasattr(post, 'is_video') and post.is_video:
                return True
            
            # Verifica se tem media_metadata (imagens/vídeos)
            if hasattr(post, 'media_metadata') and post.media_metadata:
                return True
            
            # Verifica se tem media (vídeos)
            if hasattr(post, 'media') and post.media:
                return True
            
            # Verifica se tem preview (imagens)
            if hasattr(post, 'preview') and post.preview:
                return True
            
            # Verifica se a URL é uma imagem/vídeo direto
            if not post.is_self and post.url:
                media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov']
                if any(ext in post.url.lower() for ext in media_extensions):
                    return True
                
                # Verifica se é link de vídeo conhecido
                video_domains = ['youtube.com', 'youtu.be', 'v.redd.it', 'reddit.com/gallery']
                if any(domain in post.url.lower() for domain in video_domains):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar mídia do post {post.id}: {e}")
            return False
    
    def extract_model_name(self, title: str) -> str:
        """Extrai o nome da modelo do título do post"""
        # Procura por padrão: Nome | resto do título
        match = re.search(r'^([^|]+)\s*\|', title)
        if match:
            potential_name = match.group(1).strip()
            
            # Verifica se contém pelo menos um nome próprio (palavra com letra maiúscula)
            # Remove números e caracteres especiais para análise
            clean_name = re.sub(r'[0-9@#$%^&*()_+=\[\]{};\'": ,.<>?/~`]', '', potential_name)
            words = clean_name.split()
            
            # Verifica se há pelo menos uma palavra que parece um nome (começa com maiúscula)
            has_proper_name = any(word[0].isupper() and len(word) > 1 for word in words if word)
            
            if has_proper_name:
                return potential_name
        
        return None
    
    def format_post_message(self, post) -> str:
        """Formata a mensagem do post para o Telegram"""
        # Emoji de debug baseado no tipo de conteúdo (se habilitado)
        debug_emoji = ""
        
        if self.config.get('debug_emoji', True):  # Padrão é True para compatibilidade
            debug_emoji = "📝"  # Padrão para texto
            
            if hasattr(post, 'is_video') and post.is_video:
                debug_emoji = "🎥"  # Vídeo
            elif post.url and not post.is_self:
                if any(ext in post.url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    debug_emoji = "🖼️"  # Imagem
                elif any(ext in post.url.lower() for ext in ['.mp4', '.webm', '.mov']):
                    debug_emoji = "🎬"  # Vídeo por extensão
                elif 'youtube.com' in post.url.lower() or 'youtu.be' in post.url.lower():
                    debug_emoji = "📺"  # YouTube
                elif 'reddit.com/gallery' in post.url.lower():
                    debug_emoji = "🖼️"  # Galeria Reddit
                else:
                    debug_emoji = "🔗"  # Link genérico
        
        # Extrai o nome da modelo do título
        model_name = self.extract_model_name(post.title)
        
        # Link do bot vem da configuração
        bot_link = self.config.get('bot_link', 'https://t.me/seu_bot_aqui')
        
        # Monta a mensagem personalizada com formatação melhorada
        if model_name:
            standard_message = f"""🔥 *{model_name}* • *COMPLETO NO VIP* 🔥

💎 Quer acessar o melhor conteúdo exclusivo?
🎯 *Conteúdo Premium*: Curadoria especial para membros que buscam qualidade e variedade!

🚀 *VIP COMPLETO* - [CLIQUE AQUI]({bot_link}) 🚀"""
        else:
            standard_message = f"""🔥 *COMPLETO NO VIP* 🔥

💎 Quer acessar o melhor conteúdo exclusivo?
🎯 *Conteúdo Premium*: Curadoria especial para membros que buscam qualidade e variedade!

🚀 *VIP COMPLETO* - [CLIQUE AQUI]({bot_link}) 🚀"""
        
        # Formata a mensagem com emoji e mensagem padrão (sem corpo do post)
        if debug_emoji:
            message = f"{debug_emoji}\n\n{standard_message}"
        else:
            message = standard_message
        
        return message
    
    def send_telegram_message(self, message: str, media_url: str = None, video_file_path: str = None, post_url: str = None, is_nsfw: bool = False) -> bool:
        """Envia mensagem para o Telegram com sistema de fallback"""
        bot_token = self.config['telegram']['bot_token']
        chat_id = self.config['telegram']['chat_id']
        
        if is_nsfw:
            logger.info(f"Enviando conteúdo NSFW - URL: {media_url or video_file_path}")
        
        try:
            # Se há arquivo de vídeo local, envia como vídeo
            if video_file_path and os.path.exists(video_file_path):
                url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
                
                try:
                    with open(video_file_path, 'rb') as video_file:
                        files = {'video': video_file}
                        data = {
                            'chat_id': chat_id,
                            'caption': message,
                            'parse_mode': 'Markdown'
                        }
                        
                        response = requests.post(url, files=files, data=data, timeout=120)
                        response.raise_for_status()
                        
                    logger.info("Vídeo enviado com sucesso para o Telegram")
                    return True
                    
                except requests.exceptions.RequestException as video_error:
                    logger.warning(f"Falha ao enviar vídeo: {video_error}")
                    # Adiciona à lista de mensagens falhadas
                    self.add_failed_message(message, video_file_path, post_url)
                    
                    # Tenta enviar como texto simples
                    fallback_message = f"{message}\n\n⚠️ Vídeo não pôde ser enviado"
                    if post_url:
                        fallback_message += f"\n📝 [Ver post original]({post_url})"
                    
                    return self.send_text_message(fallback_message)
                
            # Se há mídia URL, tenta enviar como foto
            elif media_url and any(ext in media_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                data = {
                    'chat_id': chat_id,
                    'photo': media_url,
                    'caption': message,
                    'parse_mode': 'Markdown'
                }
                
                try:
                    response = requests.post(url, data=data, timeout=30)
                    response.raise_for_status()
                    
                    logger.info("Foto enviada com sucesso para o Telegram")
                    return True
                    
                except requests.exceptions.RequestException as photo_error:
                    error_msg = str(photo_error)
                    if is_nsfw:
                        logger.warning(f"Falha ao enviar foto NSFW: {error_msg}")
                    else:
                        logger.warning(f"Falha ao enviar foto: {error_msg}")
                    
                    # Adiciona à lista de mensagens falhadas
                    self.add_failed_message(message, media_url, post_url)
                    
                    # Tenta enviar como texto simples
                    if is_nsfw:
                        fallback_message = f"{message}\n\n⚠️ Conteúdo não pôde ser enviado"
                    else:
                        fallback_message = f"{message}\n\n⚠️ Imagem não pôde ser enviada\n🔗 Link: {media_url}"
                    
                    if post_url:
                        fallback_message += f"\n📝 [Ver post original]({post_url})"
                    
                    return self.send_text_message(fallback_message)
                
            else:
                # Envia como mensagem de texto
                return self.send_text_message(message)
            
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar para Telegram: {e}")
            # Adiciona à lista de falhadas se houver mídia
            if media_url or video_file_path:
                self.add_failed_message(message, media_url or video_file_path, post_url)
            return False
    
    def check_subreddits(self):
        """Verifica novos posts nos subreddits configurados"""
        for subreddit_name in self.config['subreddits']:
            try:
                logger.info(f"Verificando r/{subreddit_name}")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Pega os posts mais recentes
                for post in subreddit.new(limit=self.config.get('max_posts_per_check', 10)):
                    if post.id not in self.processed_posts:
                        logger.info(f"Novo post encontrado: {post.title}")
                        
                        # Verifica se deve enviar posts apenas com texto
                        send_text_only = self.config.get('send_text_only_posts', False)
                        has_media = self.has_media_content(post)
                        
                        # Se a configuração está desabilitada e o post só tem texto, pula
                        if not send_text_only and not has_media:
                            logger.info(f"Post {post.id} pulado - apenas texto e send_text_only_posts=false")
                            self.processed_posts.add(post.id)
                            continue
                        
                        # Verifica se é conteúdo NSFW
                        is_nsfw = getattr(post, 'over_18', False)
                        if is_nsfw:
                            logger.info(f"Post NSFW detectado: {post.id}")
                        
                        # Formata a mensagem
                        message = self.format_post_message(post)
                        media_url = post.url if not post.is_self else None
                        video_file_path = None
                        
                        # Debug: mostra informações do post
                        logger.info(f"Post ID: {post.id}, is_self: {post.is_self}, URL: {post.url}, NSFW: {is_nsfw}")
                        logger.info(f"Post has is_video: {hasattr(post, 'is_video')}, is_video value: {getattr(post, 'is_video', False)}")
                        
                        # Debug detalhado das propriedades do post
                        logger.info(f"Post preview: {hasattr(post, 'preview')}")
                        logger.info(f"Post media: {hasattr(post, 'media')} - {getattr(post, 'media', None)}")
                        logger.info(f"Post media_metadata: {hasattr(post, 'media_metadata')} - {getattr(post, 'media_metadata', None)}")
                        logger.info(f"Post crosspost_parent_list: {hasattr(post, 'crosspost_parent_list')} - {getattr(post, 'crosspost_parent_list', None)}")
                        
                        # Verifica todas as propriedades que podem conter vídeo
                        if hasattr(post, 'preview') and post.preview:
                            logger.info(f"Post preview: {post.preview}")
                        if hasattr(post, 'media_metadata') and post.media_metadata:
                            logger.info(f"Post media_metadata: {post.media_metadata}")
                        if hasattr(post, 'crosspost_parent_list') and post.crosspost_parent_list:
                            logger.info(f"Post crosspost_parent_list: {post.crosspost_parent_list}")
                        
                        # Tenta baixar vídeo do Reddit (direto ou incorporado em post de texto)
                        logger.info(f"Tentando baixar vídeo do Reddit para post {post.id}")
                        video_file_path = self.download_reddit_video(post)
                        if video_file_path:
                            logger.info(f"Vídeo baixado com sucesso: {video_file_path}")
                            media_url = None  # Usa arquivo local ao invés da URL
                        else:
                            logger.info(f"Nenhum vídeo encontrado para o post {post.id}")
                            
                            # Se não encontrou vídeo, tenta baixar imagem (especialmente para posts NSFW)
                            if is_nsfw or not post.is_self:
                                logger.info(f"Tentando extrair URL de imagem para post {post.id}")
                                image_url = self.download_reddit_image(post)
                                if image_url:
                                    logger.info(f"URL da imagem extraída com sucesso: {image_url}")
                                    media_url = image_url
                                else:
                                    logger.info(f"Nenhuma imagem encontrada para o post {post.id}")
                        
                        # Envia a mensagem
                        post_url = f"https://reddit.com{post.permalink}"
                        success = self.send_telegram_message(message, media_url, video_file_path, post_url, is_nsfw)
                        
                        # Limpa arquivo temporário se foi criado
                        if video_file_path:
                            self.cleanup_temp_file(video_file_path)
                        
                        if success:
                            self.processed_posts.add(post.id)
                            # Pequena pausa entre envios
                            time.sleep(2)
                        
                        # Limita o número de posts processados por verificação
                        if len(self.processed_posts) % 5 == 0:
                            self.save_processed_posts()
                            
            except Exception as e:
                logger.error(f"Erro ao verificar r/{subreddit_name}: {e}")
                continue
    
    def run(self):
        """Executa o bot em loop contínuo"""
        logger.info("Iniciando monitoramento do Reddit...")
        logger.info(f"Subreddits monitorados: {', '.join(self.config['subreddits'])}")
        logger.info(f"Intervalo de verificação: {self.config['check_interval']} segundos")
        
        try:
            while True:
                self.check_subreddits()
                self.save_processed_posts()
                
                # Tenta reenviar mensagens falhadas a cada processamento
                self.retry_failed_messages()
                
                logger.info(f"Aguardando {self.config['check_interval']} segundos...")
                time.sleep(self.config['check_interval'])
                
        except KeyboardInterrupt:
            logger.info("Bot interrompido pelo usuário")
            self.save_processed_posts()
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            self.save_processed_posts()
            raise

def main():
    """Função principal"""
    try:
        bot = RedditToTelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"Erro ao inicializar bot: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())