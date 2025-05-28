import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configurações do painel IPTV
IPTV_BASE_URL = os.getenv('IPTV_BASE_URL', 'https://alerquina.officez.top')
IPTV_USERNAME = os.getenv('IPTV_USERNAME')
IPTV_PASSWORD = os.getenv('IPTV_PASSWORD')

def create_iptv_user(username, password, email, max_connections=2, expiry_days=30):
    """
    Cria usuário no painel IPTV Alerquina usando Form Data
    """
    try:
        # URL correta descoberta na investigação
        url = f"{IPTV_BASE_URL}/api/lines"
        
        # Headers para Form Data
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Form Data no formato correto descoberto
        form_data = {
            'key': 't-basic',
            'quick': '1',
            'method': 'post',
            'action': f'{IPTV_BASE_URL}/api/lines',
            'username': username,
            'password': password,
            'email': email,
            'name': username,  # Nome do usuário
            'connections': str(max_connections),
            'expiry_days': str(expiry_days),
            # Campos adicionais que podem ser necessários
            'package': '1',  # ID do pacote básico
            'enabled': '1',
            'admin_username': IPTV_USERNAME,
            'admin_password': IPTV_PASSWORD
        }
        
        logging.info(f"Criando usuário IPTV: {username}")
        logging.info(f"URL: {url}")
        logging.info(f"Form Data: {form_data}")
        
        # Fazer requisição POST com Form Data
        response = requests.post(
            url,
            data=form_data,  # Usar 'data' para form-urlencoded
            headers=headers,
            timeout=30,
            verify=True
        )
        
        logging.info(f"Response Status: {response.status_code}")
        logging.info(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'message' in result and 'sucesso' in result['message'].lower():
                    return {
                        'success': True,
                        'message': 'Usuário IPTV criado com sucesso',
                        'username': username,
                        'password': password,
                        'server': IPTV_BASE_URL.replace('/login', ''),
                        'connections': max_connections,
                        'expiry_days': expiry_days,
                        'response': result
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', 'Erro desconhecido'),
                        'response': result
                    }
            except:
                # Se não for JSON, considerar sucesso se status 200
                return {
                    'success': True,
                    'message': 'Usuário IPTV criado com sucesso',
                    'username': username,
                    'password': password,
                    'server': IPTV_BASE_URL.replace('/login', ''),
                    'connections': max_connections,
                    'expiry_days': expiry_days,
                    'response': response.text
                }
        else:
            return {
                'success': False,
                'error': f'Erro HTTP {response.status_code}',
                'details': response.text
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
        'endpoints': {
            'health': '/webhook/health (GET)',
            'test': '/webhook/test (POST)',
            'create_user': '/webhook/create-user (POST)'
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
            'username_set': bool(IPTV_USERNAME),
            'password_set': bool(IPTV_PASSWORD)
        }
    })

@app.route('/webhook/test', methods=['POST'])
def test_webhook():
    """Endpoint para testar webhooks"""
    try:
        data = request.get_json() or {}
        return jsonify({
            'success': True,
            'message': 'Webhook test successful',
            'received_data': data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/webhook/create-user', methods=['POST'])
def create_user_webhook():
    """
    Webhook principal para criar usuários IPTV
    Recebe dados do Make.com e cria usuário no painel
    """
    try:
        # Obter dados da requisição
        data = request.get_json() or {}
        
        # Validar campos obrigatórios
        required_fields = ['name', 'password', 'email']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'code': 'MISSING_FIELDS',
                'error': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}'
            }), 400
        
        # Extrair dados
        username = data.get('name')
        password = data.get('password')
        email = data.get('email')
        max_connections = data.get('max_connections', 2)
        expiry_days = data.get('expiry_days', 30)
        
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
        
        if '@' not in email:
            return jsonify({
                'success': False,
                'code': 'INVALID_EMAIL',
                'error': 'Email inválido'
            }), 400
        
        # Criar usuário no painel IPTV
        logging.info(f"Tentando criar usuário: {username}")
        result = create_iptv_user(username, password, email, max_connections, expiry_days)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Usuário IPTV criado com sucesso',
                'data': {
                    'username': username,
                    'email': email,
                    'server': result.get('server'),
                    'connections': max_connections,
                    'expiry_days': expiry_days,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        else:
            error_code = 'LOGIN_ERROR' if 'login' in result.get('error', '').lower() else 'CREATE_ERROR'
            return jsonify({
                'success': False,
                'code': error_code,
                'error': result.get('error', 'Falha ao criar usuário'),
                'details': result.get('details')
            }), 400
            
    except Exception as e:
        logging.error(f"Erro no webhook create-user: {str(e)}")
        return jsonify({
            'success': False,
            'code': 'INTERNAL_ERROR',
            'error': 'Erro interno do servidor',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
