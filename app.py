import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import logging
import urllib.parse
import re

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configurações do painel IPTV
IPTV_BASE_URL = os.getenv('IPTV_BASE_URL', 'https://alerquina.officez.top')
IPTV_USERNAME = os.getenv('IPTV_USERNAME')
IPTV_PASSWORD = os.getenv('IPTV_PASSWORD')

def create_iptv_user(username, email, max_connections=2, expiry_days=30):
    """
    Cria usuário no painel IPTV Alerquina
    IMPORTANTE: Painel gera senha automaticamente - NÃO enviamos senha customizada!
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
        
        # Form Data CORRIGIDO - SEM campo password (painel gera automaticamente)
        form_data = {
            'key': 't-basic',  # Campo obrigatório descoberto
            'quick': '1',      # Campo obrigatório descoberto
            'method': 'post',  # Campo obrigatório descoberto
            'action': f'{IPTV_BASE_URL}/api/lines',  # Campo obrigatório descoberto
            
            # Dados do usuário - SEM PASSWORD!
            'username': username,
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
        
        logging.info(f"=== CRIANDO USUÁRIO IPTV (SENHA AUTOMÁTICA) ===")
        logging.info(f"URL: {url}")
        logging.info(f"Username: {username}")
        logging.info(f"Email: {email}")
        logging.info(f"Form Data (sem password): {form_data}")
        
        # Fazer requisição POST com Form Data
        response = requests.post(
            url,
            data=form_data,
            headers=headers,
            timeout=30,
            verify=True,
            allow_redirects=True
        )
        
        logging.info(f"Response Status: {response.status_code}")
        logging.info(f"Response Headers: {dict(response.headers)}")
        logging.info(f"Response Text: {response.text[:1000]}...")  # Primeiros 1000 chars
        
        # Verificar resposta
        if response.status_code == 200:
            try:
                # Tentar parsear como JSON
                result = response.json()
                logging.info(f"JSON Response: {result}")
                
                # Procurar pela senha gerada na resposta
                generated_password = None
                
                # Verificar se criação foi bem-sucedida
                if isinstance(result, dict) and ('message' in result):
                    message = result.get('message', '').lower()
                    
                    if 'sucesso' in message or 'success' in message or 'gerado' in message:
                        # Tentar extrair senha da mensagem
                        # Padrões possíveis: "senha: ABC123", "password: XYZ789", etc.
                        password_patterns = [
                            r'senha[:\s]+([A-Za-z0-9]+)',
                            r'password[:\s]+([A-Za-z0-9]+)', 
                            r'pass[:\s]+([A-Za-z0-9]+)',
                            r'login[:\s]+([A-Za-z0-9]+)',
                            r'acesso[:\s]+([A-Za-z0-9]+)'
                        ]
                        
                        full_response = result.get('message', '') + str(result.get('data', ''))
                        
                        for pattern in password_patterns:
                            match = re.search(pattern, full_response, re.IGNORECASE)
                            if match:
                                generated_password = match.group(1)
                                logging.info(f"✅ Senha encontrada: {generated_password}")
                                break
                        
                        # Se não encontrou senha na mensagem, procurar em outros campos
                        if not generated_password and 'data' in result:
                            data = result['data']
                            if isinstance(data, list) and len(data) > 0:
                                item = data[0]
                                if isinstance(item, dict):
                                    # Procurar campos que podem conter a senha
                                    password_fields = ['password', 'senha', 'pass', 'login', 'access']
                                    for field in password_fields:
                                        if field in item and item[field]:
                                            generated_password = str(item[field])
                                            logging.info(f"✅ Senha encontrada no campo '{field}': {generated_password}")
                                            break
                        
                        # Se ainda não encontrou, usar senha padrão temporária
                        if not generated_password:
                            logging.warning("⚠️ Senha não encontrada na resposta, usando padrão temporário")
                            generated_password = "VERIFICAR_PAINEL"
                        
                        return {
                            'success': True,
                            'message': 'Usuário IPTV criado com sucesso',
                            'username': username,
                            'password': generated_password,  # Senha gerada pelo painel
                            'email': email,
                            'server': IPTV_BASE_URL.replace('/login', '').replace('/api/lines', ''),
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
                    # Resposta não tem estrutura esperada, mas status 200
                    # Tentar extrair senha do HTML/texto
                    response_text = response.text
                    generated_password = None
                    
                    # Procurar padrões de senha no HTML
                    password_patterns = [
                        r'senha[:\s]*([A-Za-z0-9]+)',
                        r'password[:\s]*([A-Za-z0-9]+)',
                        r'pass[:\s]*([A-Za-z0-9]+)',
                        r'Usuario.*?([A-Za-z0-9]{6,})',  # Sequência alfanumérica após "Usuario"
                    ]
                    
                    for pattern in password_patterns:
                        matches = re.findall(pattern, response_text, re.IGNORECASE)
                        if matches:
                            # Pegar o primeiro match que pareça uma senha (6+ caracteres)
                            for match in matches:
                                if len(match) >= 6 and match.isalnum():
                                    generated_password = match
                                    logging.info(f"✅ Senha extraída do HTML: {generated_password}")
                                    break
                            if generated_password:
                                break
                    
                    if not generated_password:
                        generated_password = "VERIFICAR_PAINEL"
                    
                    return {
                        'success': True,
                        'message': 'Usuário IPTV criado com sucesso',
                        'username': username,
                        'password': generated_password,
                        'email': email,
                        'server': IPTV_BASE_URL.replace('/login', '').replace('/api/lines', ''),
                        'connections': max_connections,
                        'expiry_days': expiry_days,
                        'response': response_text[:500]  # Primeiros 500 chars
                    }
                    
            except ValueError:
                # Resposta não é JSON, mas status 200 - extrair senha do texto
                response_text = response.text
                generated_password = None
                
                logging.info(f"Response não é JSON, tentando extrair senha do texto: {response_text[:200]}...")
                
                # Procurar padrões de senha no texto
                password_patterns = [
                    r'senha[:\s]*([A-Za-z0-9]+)',
                    r'password[:\s]*([A-Za-z0-9]+)',
                    r'pass[:\s]*([A-Za-z0-9]+)',
                    r'([A-Za-z0-9]{8,})',  # Qualquer sequência de 8+ caracteres alfanuméricos
                ]
                
                for pattern in password_patterns:
                    matches = re.findall(pattern, response_text, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            if len(match) >= 6 and match.isalnum():
                                generated_password = match
                                logging.info(f"✅ Senha extraída: {generated_password}")
                                break
                        if generated_password:
                            break
                
                if not generated_password:
                    generated_password = "VERIFICAR_PAINEL"
                
                return {
                    'success': True,
                    'message': 'Usuário IPTV criado com sucesso',
                    'username': username,
                    'password': generated_password,
                    'email': email,
                    'server': IPTV_BASE_URL.replace('/login', '').replace('/api/lines', ''),
                    'connections': max_connections,
                    'expiry_days': expiry_days,
                    'response': response_text[:500]
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
        'version': '3.0',
        'note': 'Painel gera senhas automaticamente',
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
                    'email': 'usuario@email.com',
                    'max_connections': 2,
                    'expiry_days': 30
                },
                'note': 'NÃO envie campo password - painel gera automaticamente'
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
            'api_endpoint': f'{IPTV_BASE_URL}/api/lines',
            'username_set': bool(IPTV_USERNAME),
            'password_set': bool(IPTV_PASSWORD)
        },
        'version': '3.0',
        'note': 'Senhas são geradas automaticamente pelo painel'
    })

@app.route('/webhook/test', methods=['POST'])
def test_webhook():
    """Endpoint para testar webhooks"""
    try:
        data = request.get_json() or {}
        
        logging.info("=== TESTE DE WEBHOOK ===")
        logging.info(f"Headers: {dict(request.headers)}")
        logging.info(f"Content-Type: {request.content_type}")
        logging.info(f"Data received: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Webhook test successful',
            'received_data': data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '3.0',
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
    IMPORTANTE: NÃO envia senha - painel gera automaticamente!
    """
    try:
        # DEBUG: Log da requisição completa
        logging.info("=== WEBHOOK CREATE-USER v3.0 (SENHA AUTOMÁTICA) ===")
        logging.info(f"Method: {request.method}")
        logging.info(f"Content-Type: {request.content_type}")
        logging.info(f"Headers: {dict(request.headers)}")
        logging.info(f"Raw data: {request.get_data()}")
        
        # Obter dados da requisição
        data = None
        
        # Tentativa 1: JSON
        try:
            data = request.get_json(force=True)
            if data:
                logging.info(f"✅ JSON parseado: {data}")
        except Exception as e:
            logging.info(f"❌ Falha ao parsear JSON: {str(e)}")
        
        # Tentativa 2: Form Data
        if not data and request.form:
            data = request.form.to_dict()
            logging.info(f"✅ Form Data: {data}")
        
        # Tentativa 3: Raw data
        if not data:
            raw_data = request.get_data(as_text=True)
            if raw_data:
                try:
                    import json
                    data = json.loads(raw_data)
                    logging.info(f"✅ Raw JSON parseado: {data}")
                except:
                    logging.info("❌ Raw data não é JSON válido")
        
        if not data:
            return jsonify({
                'success': False,
                'code': 'NO_DATA',
                'error': 'Nenhum dado recebido'
            }), 400
        
        # Validar campos obrigatórios (REMOVIDO password!)
        required_fields = ['name', 'email']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            logging.error(f"❌ Campos ausentes: {missing_fields}")
            return jsonify({
                'success': False,
                'code': 'MISSING_FIELDS',
                'error': f'Campos obrigatórios: {", ".join(required_fields)}',
                'received_data': data
            }), 400
        
        # Extrair dados (SEM password!)
        username = str(data.get('name', '')).strip()
        email = str(data.get('email', '')).strip()
        max_connections = int(data.get('max_connections', 2))
        expiry_days = int(data.get('expiry_days', 30))
        
        logging.info(f"✅ Dados extraídos - User: {username}, Email: {email}")
        logging.info(f"📝 NOTA: Senha será gerada automaticamente pelo painel!")
        
        # Validações básicas
        if len(username) < 3:
            return jsonify({
                'success': False,
                'code': 'INVALID_USERNAME',
                'error': 'Username deve ter pelo menos 3 caracteres'
            }), 400
        
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'code': 'INVALID_EMAIL',
                'error': 'Email inválido'
            }), 400
        
        # Criar usuário no painel IPTV (SEM senha customizada)
        logging.info(f"🚀 Criando usuário com senha automática: {username}")
        result = create_iptv_user(username, email, max_connections, expiry_days)
        
        if result['success']:
            logging.info(f"🎉 Usuário criado! Senha gerada: {result['password']}")
            return jsonify({
                'success': True,
                'message': 'Usuário IPTV criado com sucesso',
                'data': {
                    'username': username,
                    'password': result['password'],  # Senha gerada pelo painel
                    'email': email,
                    'server': result.get('server', IPTV_BASE_URL),
                    'connections': max_connections,
                    'expiry_days': expiry_days,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'note': 'Senha gerada automaticamente pelo painel'
                }
            })
        else:
            logging.error(f"❌ Falha: {result}")
            return jsonify({
                'success': False,
                'code': 'CREATE_ERROR',
                'error': result.get('error', 'Falha ao criar usuário'),
                'details': result.get('details')
            }), 400
            
    except Exception as e:
        logging.error(f"💥 ERRO: {str(e)}")
        logging.exception("Stack trace:")
        return jsonify({
            'success': False,
            'code': 'INTERNAL_ERROR',
            'error': 'Erro interno',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"🚀 IPTV Integration API v3.0 - Senhas Automáticas")
    logging.info(f"📡 Porta: {port}")
    logging.info(f"🌐 Base URL: {IPTV_BASE_URL}")
    logging.info(f"📝 IMPORTANTE: Painel gera senhas automaticamente!")
    
    app.run(host='0.0.0.0', port=port, debug=False)
