from flask import Flask, request, jsonify
import requests
import random
import string
import time
from bs4 import BeautifulSoup
import json
import os

app = Flask(__name__)

class IPTVWebhookIntegration:
    def __init__(self):
        self.base_url = os.getenv('IPTV_BASE_URL', 'https://alerquina.office2.top')
        self.username = os.getenv('IPTV_USERNAME')
        self.password = os.getenv('IPTV_PASSWORD')
        self.session = requests.Session()
        self.csrf_token = None
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors'
        })
    
    def login(self):
        try:
            login_page = self.session.get(f"{self.base_url}/login", timeout=30)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf'}) or soup.find('input', {'name': '_token'})
            
            if not csrf_input:
                return False
            
            login_data = {
                'csrf': csrf_input.get('value'),
                'username': self.username,
                'password': self.password
            }
            
            login_response = self.session.post(f"{self.base_url}/login", data=login_data, timeout=30)
            return login_response.status_code == 200 and 'dashboard' in login_response.url
            
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def get_csrf_token(self):
        try:
            new_page = self.session.get(f"{self.base_url}/lines/new/", timeout=30)
            soup = BeautifulSoup(new_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf'})
            
            if csrf_input:
                self.csrf_token = csrf_input.get('value')
                return True
            return False
        except Exception as e:
            print(f"CSRF error: {e}")
            return False
    
    def generate_credentials(self):
        timestamp_part = int(time.time()) % 100000000
        random_part = random.randint(10, 99)
        line_id = int(f"{timestamp_part}{random_part}")
        username = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))
        return line_id, username
    
    def create_user(self, user_data):
        try:
            if not self.login():
                return {"success": False, "error": "Falha no login", "code": "LOGIN_ERROR"}
            
            if not self.get_csrf_token():
                return {"success": False, "error": "Falha ao obter CSRF", "code": "CSRF_ERROR"}
            
            line_id, username = self.generate_credentials()
            
            create_data = {
                'csrf': self.csrf_token,
                'username': username,
                'email': user_data.get('email', ''),
                'name': user_data.get('name', ''),
                'phone': user_data.get('phone', ''),
                'phone_full': '',
                'telegram': user_data.get('telegram', ''),
                'package_id': str(user_data.get('package_id', 1)),
                'package_price': '',
                'app_id': '',
                'search_terms': '',
                'member_id': str(user_data.get('member_id', 157679)),
                'bouquet[]': str(user_data.get('bouquet_id', 78)),
                'reseller_notes': user_data.get('notes', '')
            }
            
            create_url = f"{self.base_url}/api/lines/{line_id}"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': self.base_url,
                'Referer': f"{self.base_url}/lines/new/{line_id}"
            }
            
            response = self.session.put(create_url, data=create_data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                message = result.get('message', '')
                
                if 'sucesso' in message.lower():
                    details = self.get_user_details(line_id)
                    
                    return {
                        "success": True,
                        "code": "USER_CREATED",
                        "data": {
                            "line_id": line_id,
                            "username": username,
                            "email": user_data.get('email'),
                            "name": user_data.get('name'),
                            "phone": user_data.get('phone'),
                            "telegram": user_data.get('telegram'),
                            "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                            "details": details
                        }
                    }
                else:
                    return {"success": False, "error": message, "code": "CREATE_ERROR"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}", "code": "HTTP_ERROR"}
                
        except Exception as e:
            return {"success": False, "error": str(e), "code": "EXCEPTION_ERROR"}
    
    def get_user_details(self, line_id):
        try:
            response = self.session.get(f"{self.base_url}/api/lines/{line_id}/show", timeout=30)
            return response.json() if response.status_code == 200 else None
        except:
            return None

iptv_integration = IPTVWebhookIntegration()

@app.route('/webhook/create-user', methods=['POST'])
def webhook_create_user():
    try:
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "Content-Type deve ser application/json",
                "code": "INVALID_CONTENT_TYPE"
            }), 400
        
        data = request.get_json()
        
        required_fields = ['name', 'email']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Campos obrigatórios ausentes: {', '.join(missing_fields)}",
                "code": "MISSING_FIELDS"
            }), 400
        
        result = iptv_integration.create_user(data)
        status_code = 200 if result["success"] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Erro interno: {str(e)}",
            "code": "INTERNAL_ERROR"
        }), 500

@app.route('/webhook/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "IPTV Integration Webhook",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "config": {
            "base_url": os.getenv('IPTV_BASE_URL'),
            "username_set": bool(os.getenv('IPTV_USERNAME')),
            "password_set": bool(os.getenv('IPTV_PASSWORD'))
        }
    })

@app.route('/webhook/test', methods=['POST'])
def test_webhook():
    data = request.get_json() if request.is_json else {}
    return jsonify({
        "success": True,
        "message": "Webhook funcionando!",
        "received_data": data,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "IPTV Integration API",
        "status": "running",
        "endpoints": {
            "create_user": "/webhook/create-user (POST)",
            "health": "/webhook/health (GET)",
            "test": "/webhook/test (POST)"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
