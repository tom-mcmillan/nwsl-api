from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.api_keys import create_api_key, get_user_keys, revoke_api_key

router = APIRouter()


class KeyRegistration(BaseModel):
    name: str
    email: EmailStr


@router.post("/register")
async def register_for_api_key(registration: KeyRegistration):
    """Register and receive an API key."""
    try:
        # Create the API key
        result = await create_api_key(
            name=registration.name,
            email=registration.email
        )
        
        return {
            "success": True,
            "message": "API key created successfully",
            "api_key": result['key'],
            "instructions": {
                "header": "X-API-Key",
                "example": f"curl -H 'X-API-Key: {result['key']}' https://api.nwsl.com/api/v1/teams/"
            }
        }
    except Exception as e:
        # Check if it's a duplicate
        if "unique_email_name" in str(e):
            raise HTTPException(
                status_code=400,
                detail="You already have an API key with this name. Use a different name or retrieve your existing key."
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/register", response_class=HTMLResponse)
async def registration_page():
    """Simple HTML page for API key registration."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NWSL API - Get Your API Key</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 40px;
                max-width: 500px;
                width: 100%;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 16px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 500;
            }
            input {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            input:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
            }
            button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            .result {
                margin-top: 30px;
                padding: 20px;
                background: #f5f5f5;
                border-radius: 8px;
                display: none;
            }
            .result.success {
                background: #d4edda;
                border: 1px solid #c3e6cb;
            }
            .result.error {
                background: #f8d7da;
                border: 1px solid #f5c6cb;
            }
            .api-key {
                font-family: 'Courier New', monospace;
                background: white;
                padding: 12px;
                border-radius: 6px;
                margin: 15px 0;
                word-break: break-all;
                border: 1px solid #ddd;
                position: relative;
            }
            .copy-btn {
                position: absolute;
                right: 10px;
                top: 50%;
                transform: translateY(-50%);
                background: #667eea;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                cursor: pointer;
            }
            .instructions {
                margin-top: 20px;
                padding: 15px;
                background: #e8f4ff;
                border-radius: 6px;
                font-size: 14px;
            }
            .instructions code {
                background: white;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚽ NWSL API</h1>
            <p class="subtitle">Get your API key in seconds</p>
            
            <form id="registerForm">
                <div class="form-group">
                    <label for="name">Project Name</label>
                    <input type="text" id="name" name="name" placeholder="My NWSL App" required>
                </div>
                
                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input type="email" id="email" name="email" placeholder="developer@example.com" required>
                </div>
                
                <button type="submit" id="submitBtn">Generate API Key</button>
            </form>
            
            <div id="result" class="result"></div>
        </div>
        
        <script>
            document.getElementById('registerForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const btn = document.getElementById('submitBtn');
                const resultDiv = document.getElementById('result');
                
                btn.disabled = true;
                btn.textContent = 'Creating...';
                
                const formData = {
                    name: document.getElementById('name').value,
                    email: document.getElementById('email').value
                };
                
                try {
                    const response = await fetch('/register', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        resultDiv.className = 'result success';
                        resultDiv.style.display = 'block';
                        resultDiv.innerHTML = `
                            <h3>🎉 Success!</h3>
                            <p>Your API key has been created:</p>
                            <div class="api-key">
                                <span id="apiKey">${data.api_key}</span>
                                <button class="copy-btn" onclick="copyKey()">Copy</button>
                            </div>
                            <div class="instructions">
                                <strong>How to use:</strong><br>
                                Add this header to your requests:<br>
                                <code>X-API-Key: ${data.api_key}</code>
                            </div>
                        `;
                    } else {
                        throw new Error(data.detail || 'Failed to create API key');
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.style.display = 'block';
                    resultDiv.innerHTML = `
                        <h3>❌ Error</h3>
                        <p>${error.message}</p>
                    `;
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Generate API Key';
                }
            });
            
            function copyKey() {
                const apiKey = document.getElementById('apiKey').textContent;
                navigator.clipboard.writeText(apiKey).then(() => {
                    alert('API key copied to clipboard!');
                });
            }
        </script>
    </body>
    </html>
    """


@router.get("/keys/{email}")
async def get_my_keys(email: EmailStr):
    """Get all API keys for an email address."""
    keys = await get_user_keys(email)
    
    if not keys:
        raise HTTPException(status_code=404, detail="No API keys found for this email")
    
    return {
        "email": email,
        "keys": keys,
        "total": len(keys)
    }


@router.delete("/keys/{key_id}")
async def delete_api_key(key_id: str, email: EmailStr):
    """Revoke an API key."""
    success = await revoke_api_key(key_id, email)
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found or you don't have permission to revoke it")
    
    return {
        "success": True,
        "message": "API key has been revoked"
    }