@app.route('/webhook/create-user', methods=['POST'])
def create_user_webhook():
    """
    Webhook principal para criar usuários IPTV
    Recebe dados do Make.com e cria usuário no painel
    """
    try:
        # DEBUG: Log da requisição completa
        logging.info("=== WEBHOOK CREATE-USER CHAMADO ===")
        logging.info(f"Method: {request.method}")
        logging.info(f"Content-Type: {request.content_type}")
        logging.info(f"Headers: {dict(request.headers)}")
        logging.info(f"Raw data: {request.get_data()}")
        
        # Obter dados da requisição
        data = request.get_json() or {}
        logging.info(f"Parsed JSON: {data}")
        
        # Se não conseguir parse do JSON, tentar como form
        if not data:
            data = request.form.to_dict()
            logging.info(f"Form data: {data}")
        
        # Se ainda não tiver dados, tentar raw
        if not data:
            raw_data = request.get_data(as_text=True)
            logging.info(f"Raw text data: {raw_data}")
            return jsonify({
                'success': False,
                'code': 'NO_DATA',
                'error': 'Nenhum dado recebido',
                'debug': {
                    'content_type': request.content_type,
                    'raw_data': raw_data
                }
            }), 400
        
        # Validar campos obrigatórios
        required_fields = ['name', 'password', 'email']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            logging.error(f"Campos ausentes: {missing_fields}")
            return jsonify({
                'success': False,
                'code': 'MISSING_FIELDS',
                'error': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}',
                'received_data': data
            }), 400
        
        # Extrair dados
        username = data.get('name')
        password = data.get('password')
        email = data.get('email')
        max_connections = data.get('max_connections', 2)
        expiry_days = data.get('expiry_days', 30)
        
        logging.info(f"Dados extraídos - User: {username}, Email: {email}")
        
        # Validações básicas
        if len(str(username)) < 3:
            return jsonify({
                'success': False,
                'code': 'INVALID_USERNAME',
                'error': 'Username deve ter pelo menos 3 caracteres'
            }), 400
        
        if len(str(password)) < 6:
            return jsonify({
                'success': False,
                'code': 'INVALID_PASSWORD',
                'error': 'Password deve ter pelo menos 6 caracteres'
            }), 400
        
        if '@' not in str(email):
            return jsonify({
                'success': False,
                'code': 'INVALID_EMAIL',
                'error': 'Email inválido'
            }), 400
        
        # DEBUG: Verificar variáveis de ambiente
        logging.info(f"IPTV_BASE_URL: {IPTV_BASE_URL}")
        logging.info(f"IPTV_USERNAME configurado: {bool(IPTV_USERNAME)}")
        logging.info(f"IPTV_PASSWORD configurado: {bool(IPTV_PASSWORD)}")
        
        # Criar usuário no painel IPTV
        logging.info(f"Tentando criar usuário: {username}")
        result = create_iptv_user(username, password, email, max_connections, expiry_days)
        
        if result['success']:
            logging.info("Usuário criado com sucesso!")
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
            logging.error(f"Falha ao criar usuário: {result}")
            error_code = 'LOGIN_ERROR' if 'login' in result.get('error', '').lower() else 'CREATE_ERROR'
            return jsonify({
                'success': False,
                'code': error_code,
                'error': result.get('error', 'Falha ao criar usuário'),
                'details': result.get('details')
            }), 400
            
    except Exception as e:
        logging.error(f"ERRO CRÍTICO no webhook: {str(e)}")
        logging.exception("Stack trace completo:")
        return jsonify({
            'success': False,
            'code': 'INTERNAL_ERROR',
            'error': 'Erro interno do servidor',
            'details': str(e)
        }), 500
