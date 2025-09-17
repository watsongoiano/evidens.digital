/**
 * Simplified Authentication JavaScript
 * Direct implementation for login functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Auth script loaded');
    
    let currentRole = 'medico';
    
    // Role tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all buttons
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Update current role
            currentRole = this.dataset.role;
            console.log('Role switched to:', currentRole);
            
            // Clear any error messages
            const errorDiv = document.getElementById('error-message');
            if (errorDiv) {
                errorDiv.style.display = 'none';
            }
        });
    });
    
    // Form submission
    const form = document.getElementById('login-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            handleLogin();
        });
    }
    
    // Login button click
    const loginBtn = document.querySelector('button[type="submit"]');
    if (loginBtn) {
        loginBtn.addEventListener('click', function(e) {
            e.preventDefault();
            handleLogin();
        });
    }
    
    function handleLogin() {
        console.log('Login attempt started');
        
        const email = document.querySelector('input[placeholder="Email Address"]').value;
        const password = document.querySelector('input[placeholder="Password"]').value;
        
        console.log('Email:', email, 'Role:', currentRole);
        
        if (!email || !password) {
            showError('Por favor, preencha todos os campos.');
            return;
        }
        
        // Show loading state
        const loginBtn = document.querySelector('button[type="submit"]');
        const originalText = loginBtn.textContent;
        loginBtn.textContent = 'Entrando...';
        loginBtn.disabled = true;
        
        // Make API call
        fetch(`/api/login/${currentRole}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        })
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Response data:', data);
            
            if (data.ok) {
                console.log('Login successful, redirecting to:', data.redirect);
                window.location.href = data.redirect;
            } else {
                showError(data.message || 'Erro ao fazer login. Verifique suas credenciais.');
            }
        })
        .catch(error => {
            console.error('Login error:', error);
            showError('Erro ao fazer login. Tente novamente.');
        })
        .finally(() => {
            // Reset button state
            loginBtn.textContent = originalText;
            loginBtn.disabled = false;
        });
    }
    
    function showError(message) {
        let errorDiv = document.getElementById('error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'error-message';
            errorDiv.style.cssText = `
                background-color: #fee;
                color: #c33;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                border: 1px solid #fcc;
            `;
            
            const form = document.getElementById('login-form');
            if (form) {
                form.appendChild(errorDiv);
            }
        }
        
        errorDiv.textContent = '⚠️ ' + message;
        errorDiv.style.display = 'block';
        
        // Hide error after 5 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
    
    console.log('Auth script initialized');
});
