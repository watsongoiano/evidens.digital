/**
 * Authentication JavaScript Module
 * Handles login form submission, OAuth, and user interactions
 */

class AuthManager {
    constructor() {
        this.currentRole = 'medico';
        this.isLoading = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupAccessibility();
    }

    bindEvents() {
        // Role tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => this.switchRole(e));
        });

        // Form submission
        const form = document.getElementById('login-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleLogin(e));
        }

        // OAuth buttons
        const googleBtn = document.getElementById('google-login');
        if (googleBtn) {
            googleBtn.addEventListener('click', (e) => this.handleGoogleLogin(e));
        }

        const microsoftBtn = document.getElementById('microsoft-login');
        if (microsoftBtn) {
            microsoftBtn.addEventListener('click', (e) => this.handleMicrosoftLogin(e));
        }

        // Forgot password
        const forgotLink = document.getElementById('forgot-password');
        if (forgotLink) {
            forgotLink.addEventListener('click', (e) => this.handleForgotPassword(e));
        }

        // Create account
        const createAccountLink = document.getElementById('create-account');
        if (createAccountLink) {
            createAccountLink.addEventListener('click', (e) => this.handleCreateAccount(e));
        }

        // Real-time form validation
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');

        if (emailInput) {
            emailInput.addEventListener('blur', () => this.validateEmail());
            emailInput.addEventListener('input', () => this.clearFieldError('email'));
        }

        if (passwordInput) {
            passwordInput.addEventListener('input', () => this.clearFieldError('password'));
        }
    }

    setupAccessibility() {
        // Add ARIA labels and descriptions
        const form = document.getElementById('login-form');
        if (form) {
            form.setAttribute('novalidate', '');
        }

        // Keyboard navigation for tabs
        document.querySelectorAll('.tab-button').forEach((button, index, buttons) => {
            button.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                    e.preventDefault();
                    const nextIndex = e.key === 'ArrowRight' 
                        ? (index + 1) % buttons.length 
                        : (index - 1 + buttons.length) % buttons.length;
                    buttons[nextIndex].click();
                    buttons[nextIndex].focus();
                }
            });
        });
    }

    switchRole(event) {
        event.preventDefault();
        
        const button = event.target;
        const role = button.dataset.role;
        
        if (role === this.currentRole) return;
        
        // Update active tab
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
            btn.setAttribute('aria-selected', 'false');
        });
        
        button.classList.add('active');
        button.setAttribute('aria-selected', 'true');
        
        this.currentRole = role;
        this.clearErrors();
        
        // Announce role change to screen readers
        this.announceToScreenReader(`Switched to ${role === 'medico' ? 'Medical Professional' : 'Administrator'} login`);
    }

    async handleLogin(event) {
        event.preventDefault();
        
        if (this.isLoading) return;
        
        const formData = new FormData(event.target);
        const email = formData.get('email')?.trim();
        const password = formData.get('password');
        const remember = formData.get('remember') === 'on';
        
        // Client-side validation
        if (!this.validateForm(email, password)) {
            return;
        }
        
        this.setLoading(true);
        this.clearErrors();
        
        try {
            const response = await fetch(`/api/login/${this.currentRole}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    email: email,
                    password: password,
                    remember: remember
                })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                this.handleLoginSuccess(data);
            } else {
                this.handleLoginError(data, response.status);
            }
            
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Erro de conexão. Verifique sua internet e tente novamente.');
        } finally {
            this.setLoading(false);
        }
    }

    validateForm(email, password) {
        let isValid = true;
        
        // Email validation
        if (!email) {
            this.showFieldError('email', 'Email é obrigatório');
            isValid = false;
        } else if (!this.isValidEmail(email)) {
            this.showFieldError('email', 'Email inválido');
            isValid = false;
        }
        
        // Password validation
        if (!password) {
            this.showFieldError('password', 'Senha é obrigatória');
            isValid = false;
        } else if (password.length < 6) {
            this.showFieldError('password', 'Senha deve ter pelo menos 6 caracteres');
            isValid = false;
        }
        
        return isValid;
    }

    validateEmail() {
        const emailInput = document.getElementById('email');
        const email = emailInput.value.trim();
        
        if (email && !this.isValidEmail(email)) {
            this.showFieldError('email', 'Email inválido');
            return false;
        }
        
        this.clearFieldError('email');
        return true;
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    showFieldError(fieldName, message) {
        const input = document.getElementById(fieldName);
        if (input) {
            input.setAttribute('aria-invalid', 'true');
            input.classList.add('error');
            
            // Create or update error message
            let errorElement = document.getElementById(`${fieldName}-error`);
            if (!errorElement) {
                errorElement = document.createElement('div');
                errorElement.id = `${fieldName}-error`;
                errorElement.className = 'field-error';
                errorElement.setAttribute('role', 'alert');
                input.parentNode.appendChild(errorElement);
            }
            
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }
    }

    clearFieldError(fieldName) {
        const input = document.getElementById(fieldName);
        if (input) {
            input.setAttribute('aria-invalid', 'false');
            input.classList.remove('error');
            
            const errorElement = document.getElementById(`${fieldName}-error`);
            if (errorElement) {
                errorElement.style.display = 'none';
            }
        }
    }

    handleLoginSuccess(data) {
        this.announceToScreenReader('Login realizado com sucesso');
        
        // Store user info if needed
        if (data.user) {
            sessionStorage.setItem('user', JSON.stringify(data.user));
        }
        
        // Redirect to dashboard
        window.location.href = data.redirect || '/dashboard';
    }

    handleLoginError(data, status) {
        let errorMessage = 'Erro desconhecido';
        
        switch (data.error) {
            case 'INVALID_CREDENTIALS':
                errorMessage = 'Email ou senha incorretos';
                break;
            case 'ACCOUNT_LOCKED':
                const minutes = Math.ceil(data.retry_after_sec / 60);
                errorMessage = `Conta bloqueada. Tente novamente em ${minutes} minutos`;
                break;
            case 'EMAIL_PASSWORD_REQUIRED':
                errorMessage = 'Email e senha são obrigatórios';
                break;
            case 'INVALID_EMAIL_FORMAT':
                errorMessage = 'Formato de email inválido';
                break;
            case 'RATE_LIMIT_EXCEEDED':
                errorMessage = data.message || 'Muitas tentativas. Tente novamente mais tarde';
                break;
            case 'USER_NOT_FOUND':
                errorMessage = 'Usuário não encontrado';
                break;
            case 'WRONG_ROLE':
                errorMessage = `Esta conta não tem permissão para acessar como ${this.currentRole === 'medico' ? 'profissional de saúde' : 'administrador'}`;
                break;
            default:
                errorMessage = data.message || 'Erro ao fazer login. Tente novamente';
        }
        
        this.showError(errorMessage);
    }

    showError(message) {
        const errorElement = document.getElementById('error-message');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            errorElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            
            // Focus on error for screen readers
            errorElement.focus();
        }
    }

    clearErrors() {
        const errorElement = document.getElementById('error-message');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
        
        // Clear field errors
        ['email', 'password'].forEach(field => {
            this.clearFieldError(field);
        });
    }

    setLoading(loading) {
        this.isLoading = loading;
        
        const button = document.getElementById('login-btn');
        const buttonText = button.querySelector('.button-text');
        const spinner = button.querySelector('.loading-spinner');
        
        if (loading) {
            button.disabled = true;
            buttonText.style.opacity = '0';
            spinner.style.display = 'block';
            button.setAttribute('aria-label', 'Fazendo login...');
        } else {
            button.disabled = false;
            buttonText.style.opacity = '1';
            spinner.style.display = 'none';
            button.setAttribute('aria-label', 'Entrar');
        }
    }

    async handleGoogleLogin(event) {
        event.preventDefault();
        
        try {
            // Redirect to Google OAuth
            window.location.href = `/api/login/google?role=${this.currentRole}`;
        } catch (error) {
            console.error('Google login error:', error);
            this.showError('Erro ao conectar com Google. Tente novamente.');
        }
    }

    async handleMicrosoftLogin(event) {
        event.preventDefault();
        
        try {
            // Redirect to Microsoft OAuth
            window.location.href = `/api/login/microsoft?role=${this.currentRole}`;
        } catch (error) {
            console.error('Microsoft login error:', error);
            this.showError('Erro ao conectar com Microsoft. Tente novamente.');
        }
    }

    handleForgotPassword(event) {
        event.preventDefault();
        
        const email = document.getElementById('email').value.trim();
        
        if (!email) {
            this.showError('Digite seu email primeiro para recuperar a senha');
            document.getElementById('email').focus();
            return;
        }
        
        if (!this.isValidEmail(email)) {
            this.showError('Digite um email válido para recuperar a senha');
            document.getElementById('email').focus();
            return;
        }
        
        this.showForgotPasswordModal(email);
    }

    async showForgotPasswordModal(email) {
        const confirmed = confirm(`Enviar link de recuperação para ${email}?`);
        
        if (!confirmed) return;
        
        try {
            const response = await fetch('/api/forgot-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                alert('Se o email existir, um link de recuperação foi enviado.');
            } else {
                this.showError(data.message || 'Erro ao enviar email de recuperação');
            }
        } catch (error) {
            console.error('Forgot password error:', error);
            this.showError('Erro ao enviar email de recuperação');
        }
    }

    handleCreateAccount(event) {
        event.preventDefault();
        
        // For now, show a message that account creation is admin-only
        alert('A criação de contas é restrita a administradores. Entre em contato com o administrador do sistema.');
    }

    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }
}

// Utility function to check if user is already logged in
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/me', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.ok && data.user) {
                // User is already logged in, redirect to dashboard
                window.location.href = '/dashboard';
                return;
            }
        }
    } catch (error) {
        // Not logged in or error, continue with login page
        console.log('Not logged in, showing login page');
    }
}

// Handle OAuth callbacks
function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    const success = urlParams.get('success');
    
    if (error) {
        const authManager = new AuthManager();
        authManager.showError(decodeURIComponent(error));
    } else if (success) {
        // OAuth success, redirect to dashboard
        window.location.href = '/dashboard';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is already authenticated
    checkAuthStatus();
    
    // Handle OAuth callbacks
    handleOAuthCallback();
    
    // Initialize auth manager
    window.authManager = new AuthManager();
});

// Add CSS for field errors
const style = document.createElement('style');
style.textContent = `
    .field-error {
        color: var(--error-color, #E74C3C);
        font-size: 0.875rem;
        margin-top: 0.25rem;
        display: none;
    }
    
    .input-wrapper input.error {
        border-color: var(--error-color, #E74C3C);
        box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.1);
    }
    
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
`;
document.head.appendChild(style);
