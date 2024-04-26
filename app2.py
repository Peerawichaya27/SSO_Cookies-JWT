from flask import Flask, request, redirect, make_response, render_template_string
import requests

app = Flask(__name__)

# Simulated user data
users = {
    "user1": {"password": "password1", "role": "user"},
    "user2": {"password": "password2", "role": "admin"}
}

@app.route('/')
def home():
    return render_template_string('''
        <h1>Welcome to App2</h1>
        <form action="/login" method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
            <a href="/protected">SSO</a>
        </form>
    ''')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = users.get(username)
    if user and user['password'] == password:
        # Send user data to Authentication Service 1
        auth_response = requests.post('http://localhost:5001/authenticate', json={'username': username, 'password': password, 'role': user['role']})
        if auth_response.status_code == 200:
            # Authenticate with SSO service
            user_info = {'username': username, 'role': user['role']}
            sso_response = requests.post('http://localhost:5000/authenticate', json=user_info)
            if sso_response.status_code == 200:
                resp = make_response(redirect('/protected'))
                resp.set_cookie('sso_token', sso_response.json()['sso_token'], httponly=True, secure=True, samesite='Lax')
                return resp
            return 'SSO Service Error', sso_response.status_code
        return 'Authentication Service Error', auth_response.status_code
    return 'Invalid Credentials', 401

@app.route('/protected')
def protected():
    token = request.cookies.get('sso_token')
    if token:
        # Verify token with SSO service
        verify_response = requests.get('http://localhost:5000/verify', cookies={'sso_token': token})
        if verify_response.status_code == 200:
            username = verify_response.json()['username']
            role = verify_response.json()['role']
            return render_template_string(f'''
                <h1>Protected Content</h1>
                <p>Username: {username}</p>
                <p>Role: {role}</p>
                <a href="/logout">Home</a>
            ''')
    return 'Access denied <a href="/">Login</a>', 403

@app.route('/logout')
def logout():
    resp = make_response(redirect('/'))
    resp.set_cookie('sso_token', '', expires=0)
    return resp

if __name__ == '__main__':
    app.run(port=5102, debug=True)