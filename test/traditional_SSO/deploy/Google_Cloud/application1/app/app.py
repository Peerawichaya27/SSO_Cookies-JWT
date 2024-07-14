from flask import Flask, request, redirect, make_response, render_template_string, jsonify
from flask_cors import CORS, cross_origin
import requests
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import base64
import jwt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sso_secret_key'
ALGORITHM = 'HS256'
CORS(app)

# Simulated user data
users = {
    "user1": {"password": "pass1", "role": "admin"}
}

user_role = {
    "admin": "35a3716d343040c666a071477427535ada70f74ceee8b9d9058d4412cbe40c52",
    "users": "0b35b922fd1c5853cf65b737f49c49d8ef750946b5939443056d94b3a3510dc6"
}

user_permission = {
    "admin": {"Read, Write, Execute"},
    "users": {"Read, Write"}
}

permission_hash = {
    "admin": "138c4b0b96c01b0715d870c11c0853592aa32137c421e73827821fe14c9aab6e",
    "users": "f6e72ec20d183ec2fcb6a11ec25eb944696ad2ba50569fc7264ad1ee363bf105"
}

pKey = """-----BEGIN RSA PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0gr6/AuK3Z+LSQ7sR4z0
9b4sdb9roDjgKLTkQoa9yjaFO2oJsQ3fpmx7SFbW57qjAL1VH8hFpfb1CGzXONXc
4IramDHFZPORLw6bi5PsTuEDuj45LURkVKIYoKKD7OP/jxNbuPn0l2wc6drveZnY
Dw0xPk4BGrCse6Tg1zLiizH5b1hKbjeFrWu4lCHsbHnwyN7YRakpq4bwsACdYyYS
h6Qze5hC05pcjKwW7/VNq85G2nmCjp8Elz5VDybJdgE5IkxG7XDIq8N64ozdFti6
wp19pzBQs8rMd45LiheVf/7ubSe+QxRw/uVmIeYWaYkoo69NjffhTCFdnA/4mwHJ
yQIDAQAB
-----END RSA PUBLIC KEY-----"""

@app.route('/')
@cross_origin()
def home():
    return render_template_string('''
        <h1>Welcome to App1</h1>
        <form action="/login" method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
            <a href="/protected">SSO</a>
        </form>
    ''')

def unpadded_token(padded_token):
    try:
        padded_bytes = base64.urlsafe_b64decode(padded_token)
        token_bytes = padded_bytes[128:-128]
        unperturbed_bytes = token_bytes
        unpadded_token = unperturbed_bytes.decode()
        return unpadded_token
    except Exception as e:
        print(f"Error during unpadding: {e}")
        return None

def verify_token(signed_token):
    try:
        token_part, sig_hex = signed_token.rsplit('.', 1)
        signature = bytes.fromhex(sig_hex)
        key = RSA.import_key(pKey.strip())
        hasher = SHA256.new(token_part.encode())
        pkcs1_15.new(key).verify(hasher, signature)
        return True
    except (ValueError, TypeError):
        return False

@app.route('/login', methods=['POST', 'GET'])
@cross_origin()
def login():
    username = request.form['username']
    password = request.form['password']
    auth_response = requests.post('https://auth-service1-hlcp4m5f5q-as.a.run.app/authenticate', json={'username': username, 'password': password, 'appNo': 'app1'})
    if auth_response.status_code == 200:
        resp = make_response(redirect('/protected'))
        return resp
    return 'Authentication Service Error', auth_response.status_code

# for test
@app.route('/generate_token', methods=['GET'])
@cross_origin()
def generate_token():
    sso_response = requests.get('http://localhost:5200/authenticate', headers={'username': 'user1', 'appNo': 'app1'})
    sso_token = sso_response.json()['sso_token']
    return jsonify({'sso_token': sso_token}), 200

# for test
@app.route('/verify_token', methods=['POST'])
@cross_origin()
def verify_token_endpoint():
    sso_token = request.json.get('sso_token')
    sign_token = unpadded_token(sso_token)
    if sso_token and verify_token(sign_token):
        sign_token = sign_token.rsplit('.', 1)[0]
        decoded = jwt.decode(sign_token, app.config['SECRET_KEY'], algorithms=[ALGORITHM])
        username = decoded["userID"]
        rolehash = decoded['roles']
        permissionhash = decoded['permissions']
        if rolehash['app1'] == user_role["admin"]:
            role = "admin"
            if permissionhash['app1'] == permission_hash["admin"]:
                permission = user_permission["admin"]
            else:
                return jsonify({'message': 'Access denied'}), 403
        elif rolehash['app1'] == user_role["users"]:
            role = "user"
            if permissionhash['app1'] == permission_hash["users"]:
                permission = user_permission['users']
            else:
                return jsonify({'message': 'Access denied'}), 403
        else:
            return jsonify({'message': 'Access denied'}), 403
        return jsonify({'username': username, 'role': role, 'permissions': list(permission)}), 200
    return jsonify({'message': 'Access denied'}), 403

@app.route('/protected')
@cross_origin()
def protected():
    sso_response = requests.get('http://localhost:5200/authenticate', headers={'username': 'user1', 'appNo': 'app1'})
    sso_token = sso_response.json()['sso_token']
    sign_token = unpadded_token(sso_token)
    if sso_token and verify_token(sign_token):
        sign_token = sign_token.rsplit('.', 1)[0]
        decoded = jwt.decode(sign_token, app.config['SECRET_KEY'], algorithms=[ALGORITHM])
        username = decoded["userID"]
        rolehash = decoded['roles']
        permissionhash = decoded['permissions']
        if rolehash['app1'] == user_role["admin"]:
            role = "admin"
            if permissionhash['app1'] == permission_hash["admin"]:
                permission = user_permission["admin"]
            else:
                return 'Access denied <a href="/">Login</a>', 403
        elif rolehash['app1'] == user_role["users"]:
            role = "user"
            if permissionhash['app1'] == permission_hash["users"]:
                permission = user_permission['users']
            else:
                return 'Access denied <a href="/">Login</a>', 403
        else:
            return 'Access denied <a href="/">Login</a>', 403
        return render_template_string(f'''
                <h1>Protected Content</h1>
                <p>Username: {username}</p>
                <p>Role: {role}</p>
                <p>Permissions: {permission}</p>
                <a href="/logout">Logout</a>
            ''')
    return 'Access denied <a href="/">Login</a>', 403

@app.route('/logout')
@cross_origin()
def logout():
    resp = make_response(redirect('/'))
    resp.set_cookie('sso_token', '', expires=0)
    return resp

if __name__ == '__main__':
    app.run(port=5201, debug=True)
