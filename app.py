import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import logging
import urllib.parse

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configurações do painel IPTV - CORRIGIDAS baseadas na investigação
IPTV_BASE_URL = os.getenv('IPTV_BASE_URL', 'https://alerquina.officez.top')
IPTV_USERNAME = os.getenv('IPTV_USERNAME')
IPTV_PASSWORD = os.getenv('IPTV_PASSWORD')

def create_iptv_user(username, password, email, max_connections=2, expiry_days=30):
    """
    Cria usuário no painel IPTV Alerquina usando descobertas da investigação DevTools
    """
    try:
        # URL CORRETA descoberta na investigação: /api/lines
        url = f"{IPTV_BASE_URL}/api/lines"
        
        # Headers para Form Data (descoberto na investigação)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # Form Data EXATO descoberto na investigação DevTools
        form_data = {
            'key': 't-basic',  # Campo obrigatório descoberto
            'quick': '1',      # Campo obrigatório descoberto
            'method': 'post',  # Campo obrigatório descoberto
            'action': f'{IPTV_BASE_URL}/api/lines',  # Campo obrigatório descoberto
            
            # Dados do usuário
            'username': username,
            'password': password,
            'email': email,
            'name': username,
            
            # Configurações do usuário IPTV
            'connections': str(max_connections),
            'expiry_days': str(expiry_days),
            'enabled': '1',
            'package': '1',  # ID do pacote básico
            
            # Credenciais admin (se necessário)
            'admin_username': IPTV_USERNAME,
            'admin_password': IPTV_PASSWORD
        }
        
        logging.info(f"=== CRIANDO USUÁRIO IPTV ===")
        logging.info(f"URL: {url}")
        logging.info(f"Username: {username}")
        logging.info(f"Email: {email}")
        logging.info(f"Form Data: {form_data}")
        
        # Fazer requisição POST com Form Data (formato correto)
        response = requests.post(
            url,
            data=form_data,  # IMPORTANTE: usar 'data' para form-urlencoded
            headers=headers,
            timeout=30,
            verify=True,
            allow_redirects=True
        )
        
        logging.info(f"Response Status: {response.status_code}")
        logging.info(f"Response Headers: {dict(response.headers)}")
        logging.info(f"Response Text: {response.text[:500]}...")  # Primeiros 500 chars
        
        # Verificar resposta
        if response.status_code == 200:
            try:
                # Tentar parsear como JSON
                result = response.json()
                
                # Verificar se criação foi bem-sucedida
                if isinstance(result, dict) and ('message' in result):
                    message = result.get('message', '').lower()
                    if 'sucesso' in message or 'success' in message or 'gerado' in message:
                        return {
                            'success': True,
                            'message': 'Usuário IPTV criado com sucesso',
                            'username': username,
                            'password': password,
                            'email': email,
                            'server': IPTV_BASE_URL.replace('/login', ''),
                            'connections': max_connections,
                            'expiry_days': expiry_days,
                            'response': result
                        }
                    else:
                        return {
                            'success': False,
                            'error': result.get('message', 'Erro na criação do usuário'),
                            'response': result
                        }
                else:
                    # Se resposta não tem estrutura esperada, mas status 200
                    return {
                        'success': True,
                        'message': 'Usuário IPTV criado com sucesso (resposta inesperada)',
                        'username': username,
                        'password': password,
                        'email': email,
                        'server': IPTV_BASE_URL.replace('/login', ''),
                        'connections': max_connections,
                        'expiry_days': expiry_days,
                        'response': response.text
                    }
                    
            except ValueError:
                # Resposta não é JSON válido, mas status 200
                if len(response.text) < 1000:  # Se resposta é pequena, pode ser sucesso
                    return {
                        'success': True,
                        'message': 'Usuário IPTV criado com sucesso',
                        'username': username,
                        'password': password,
                        'email': email,
                        'server': IPTV_BASE_URL.replace('/login', ''),
                        'connections': max_connections,
                        'expiry_days': expiry_days,
                        'response': response.text
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Resposta inválida do servidor',
                        'details': response.text[:500]
                    }
        else:
            return {
                'success': False,
                'error': f'Erro HTTP {response.status_code}',
                'details': response.text[:500]
            }
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de conexão: {str(e)}")
        return {
            'success': False,
            'error': 'CONEXAO_ERROR',
            'details': f'Erro de conexão: {str(e)}'
        }
    except Exception as e:
        logging.error(f"Erro inesperado: {str(e)}")
        return {
            'success': False,
            'error': 'ERRO_INTERNO',
            'details': f'Erro interno: {str(e)}'
        }

@app.route('/', methods=['GET'])
def home():
    """Endpoint principal da API"""
    return jsonify({
        'service': 'IPTV Integration API',
        'status': 'running',
        'version': '2.0',
        'endpoints': {
            'health': '/webhook/health (GET)',
            'test': '/webhook/test (POST)',
            'create_user': '/webhook/create-user (POST)'
        },
        'docs': {
            'create_user_example': {
                'url': '/webhook/create-user',
                'method': 'POST',
                'headers': {'Content-Type': 'application/json'},
                'body': {
                    'name': 'usuario123',
                    'password': 'senha123',
                    'email': 'usuario@email.com',
                    'max_connections': 2,
                    'expiry_days': 30
                }
            }
        }
    })

@app.route('/webhook/health', methods=['GET'])
def health_check():
    """Verifica se a API e configurações estão funcionando"""
    return jsonify({
        'service': 'IPTV Integration Webhook',
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'config': {
            'base_url': IPTV_BASE_URL,
            'api_endpoint': f'{IPTV_BASE_URL}/api/lines',  # Endpoint correto
            'username_set': bool(IPTV_USERNAME),
            'password_set': bool(IPTV_PASSWORD)
        },
        'version': '2.0'
    })

@app.route('/webhook/test', methods=['POST'])
def test_webhook():
    """Endpoint para testar webhooks"""
    try:
        data = request.get_json() or {}
        
        # Log detalhado para debug
        logging.info("=== TESTE DE WEBHOOK ===")
        logging.info(f"Headers: {dict(request.headers)}")
        logging.info(f"Content-Type: {request.content_type}")
        logging.info(f"Data received: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Webhook test successful',
            'received_data': data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'debug_info': {
                'content_type': request.content_type,
                'method': request.method,
                'headers': dict(request.headers)
            }
        })
    except Exception as e:
        logging.error(f"Erro no teste: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/webhook/create-user', methods=['POST'])
def create_user_webhook():
    """
    Webhook principal para criar usuários IPTV
    Recebe dados do Make.com e cria usuário no painel Alerquina
    """
    try:
        # DEBUG: Log da requisição completa
        logging.info("=== WEBHOOK CREATE-USER INICIADO ===")
        logging.info(f"Method: {request.method}")
        logging.info(f"Content-Type: {request.content_type}")
        logging.info(f"Headers: {dict(request.headers)}")
        logging.info(f"Raw data: {request.get_data()}")
        logging.info(f"Args: {dict(request.args)}")
        logging.info(f"Form: {dict(request.form)}")
        
        # Obter dados da requisição - múltiplas tentativas
        data = None
        
        # Tentativa 1: JSON
        try:
            data = request.get_json(force=True)
            if data:
                logging.info(f"✅ JSON parseado com sucesso: {data}")
        except Exception as e:
            logging.info(f"❌ Falha ao parsear JSON: {str(e)}")
        
        # Tentativa 2: Form Data
        if not data and request.form:
            data = request.form.to_dict()
            logging.info(f"✅ Form Data encontrado: {data}")
        
        # Tentativa 3: Raw data
        if not data:
            raw_data = request.get_data(as_text=True)
            logging.info(f"Raw text data: {raw_data}")
            
            # Tentar parsear raw data como JSON
            if raw_data:
                try:
                    import json
                    data = json.loads(raw_data)
                    logging.info(f"✅ Raw JSON parseado: {data}")
                except:
                    logging.info("❌ Raw data não é JSON válido")
        
        # Verificar se conseguiu obter dados
        if not data:
            return jsonify({
                'success': False,
                'code': 'NO_DATA',
                'error': 'Nenhum dado recebido ou formato inválido',
                'debug': {
                    'content_type': request.content_type,
                    'method': request.method,
                    'has_json': bool(request.is_json),
                    'has_form': bool(request.form),
                    'raw_data_length': len(request.get_data())
                }
            }), 400
        
        # Validar campos obrigatórios
        required_fields = ['name', 'password', 'email']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            logging.error(f"❌ Campos ausentes: {missing_fields}")
            return jsonify({
                'success': False,
                'code': 'MISSING_FIELDS',
                'error': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}',
                'received_data': data,
                'required_fields': required_fields
            }), 400
        
        # Extrair e validar dados
        username = str(data.get('name', '')).strip()
        password = str(data.get('password', '')).strip()
        email = str(data.get('email', '')).strip()
        max_connections = int(data.get('max_connections', 2))
        expiry_days = int(data.get('expiry_days', 30))
        
        logging.info(f"✅ Dados extraídos - User: {username}, Email: {email}, Connections: {max_connections}")
        
        # Validações básicas
        if len(username) < 3:
            return jsonify({
                'success': False,
                'code': 'INVALID_USERNAME',
                'error': 'Username deve ter pelo menos 3 caracteres'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'code': 'INVALID_PASSWORD',
                'error': 'Password deve ter pelo menos 6 caracteres'
            }), 400
        
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'code': 'INVALID_EMAIL',
                'error': 'Email inválido'
            }), 400
        
        # DEBUG: Verificar configurações
        logging.info(f"🔧 Configurações:")
        logging.info(f"   IPTV_BASE_URL: {IPTV_BASE_URL}")
        logging.info(f"   IPTV_USERNAME: {'✅ Configurado' if IPTV_USERNAME else '❌ Não configurado'}")
        logging.info(f"   IPTV_PASSWORD: {'✅ Configurado' if IPTV_PASSWORD else '❌ Não configurado'}")
        
        # Criar usuário no painel IPTV
        logging.info(f"🚀 Iniciando criação do usuário: {username}")
        result = create_iptv_user(username, password, email, max_connections, expiry_days)
        
        if result['success']:
            logging.info("🎉 Usuário criado com sucesso!")
            return jsonify({
                'success': True,
                'message': 'Usuário IPTV criado com sucesso',
                'data': {
                    'username': username,
                    'password': password,  # Incluir senha para o email
                    'email': email,
                    'server': result.get('server', IPTV_BASE_URL),
                    'connections': max_connections,
                    'expiry_days': expiry_days,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'login_url': f"{IPTV_BASE_URL}/login",
                    'api_response': result.get('response')
                }
            })
        else:
            logging.error(f"❌ Falha ao criar usuário: {result}")
            error_code = 'LOGIN_ERROR' if 'login' in result.get('error', '').lower() else 'CREATE_ERROR'
            return jsonify({
                'success': False,
                'code': error_code,
                'error': result.get('error', 'Falha ao criar usuário'),
                'details': result.get('details'),
                'debug_info': result
            }), 400
            
    except Exception as e:
        logging.error(f"💥 ERRO CRÍTICO no webhook: {str(e)}")
        logging.exception("Stack trace completo:")
        return jsonify({
            'success': False,
            'code': 'INTERNAL_ERROR',
            'error': 'Erro interno do servidor',
            'details': str(e)
        }), 500

# Rota adicional para debug (remover em produção)
@app.route('/webhook/debug', methods=['GET', 'POST'])
def debug_webhook():
    """Endpoint para debug - mostra todas as informações da requisição"""
    return jsonify({
        'method': request.method,
        'headers': dict(request.headers),
        'args': dict(request.args),
        'form': dict(request.form),
        'json': request.get_json(silent=True),
        'data': request.get_data(as_text=True),
        'content_type': request.content_type,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logging.info(f"🚀 Iniciando IPTV Integration API v2.0")
    logging.info(f"📡 Porta: {port}")
    logging.info(f"🔧 Debug: {debug_mode}")
    logging.info(f"🌐 Base URL: {IPTV_BASE_URL}")
    logging.info(f"👤 Username configurado: {bool(IPTV_USERNAME)}")
    logging.info(f"🔑 Password configurado: {bool(IPTV_PASSWORD)}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
