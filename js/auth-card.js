(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        const tabButtons = document.querySelectorAll('.tab-button');
        const loginForm = document.getElementById('login-form');
        const loginButton = document.getElementById('login-btn');
        const loginButtonText = loginButton?.querySelector('.button-text');
        const loginSpinner = loginButton?.querySelector('.loading-spinner');
        const feedbackMessage = document.getElementById('feedback-message');
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');
        const forgotPasswordLink = document.getElementById('forgot-password');
        const googleLoginButton = document.getElementById('google-login');
        const microsoftLoginButton = document.getElementById('microsoft-login');

        const activeTab = document.querySelector('.tab-button.active');
        let currentRole = activeTab?.dataset.role || 'medico';

        const errorMessages = {
            INVALID_CREDENTIALS: 'We could not find an account with those credentials.',
            INVALID_EMAIL_FORMAT: 'Please enter a valid email address.',
            EMAIL_PASSWORD_REQUIRED: 'Email and password are required.',
            ACCOUNT_LOCKED: 'Too many failed attempts. Please try again in a few minutes.',
            JSON_REQUIRED: 'Something went wrong with the request. Please try again.',
            INVALID_ROLE: 'The selected role is not available for this account.'
        };

        function setRole(role, button) {
            currentRole = role || 'medico';
            tabButtons.forEach((btn) => {
                btn.classList.toggle('active', btn === button);
                btn.setAttribute('aria-pressed', btn === button ? 'true' : 'false');
            });
        }

        function setFeedback(message, type = 'error') {
            if (!feedbackMessage) {
                return;
            }

            feedbackMessage.textContent = message;

            if (!message) {
                feedbackMessage.style.display = 'none';
                feedbackMessage.classList.remove('feedback-error', 'feedback-success');
                return;
            }

            feedbackMessage.style.display = 'block';
            feedbackMessage.classList.toggle('feedback-success', type === 'success');
            feedbackMessage.classList.toggle('feedback-error', type !== 'success');
        }

        function setLoading(isLoading) {
            if (!loginButton) {
                return;
            }

            loginButton.disabled = isLoading;
            loginButton.setAttribute('aria-busy', String(isLoading));

            if (loginButtonText) {
                loginButtonText.textContent = isLoading ? 'Signing in…' : 'Sign in';
            }

            if (loginSpinner) {
                loginSpinner.style.display = isLoading ? 'inline-flex' : 'none';
            }

            loginButton.classList.toggle('is-loading', isLoading);
        }

        function normalizeResponse(data) {
            if (Array.isArray(data)) {
                return data[0];
            }
            return data;
        }

        function resolveErrorMessage(payload, statusCode) {
            if (!payload || typeof payload !== 'object') {
                return 'Unable to sign in at the moment. Please try again.';
            }

            if (payload.error === 'ACCOUNT_LOCKED' && payload.retry_after_sec) {
                const minutes = Math.max(1, Math.ceil(payload.retry_after_sec / 60));
                return `Too many attempts. Try again in approximately ${minutes} minute${minutes > 1 ? 's' : ''}.`;
            }

            if (payload.error && errorMessages[payload.error]) {
                return errorMessages[payload.error];
            }

            if (statusCode >= 500) {
                return 'Our servers are unavailable right now. Please try again later.';
            }

            return payload.message || 'Unable to sign in. Please check your credentials and try again.';
        }

        async function handleLogin(event) {
            event?.preventDefault();
            if (!emailInput || !passwordInput) {
                return;
            }

            const email = emailInput.value.trim();
            const password = passwordInput.value.trim();

            if (!email || !password) {
                setFeedback('Please enter your email and password to continue.');
                return;
            }

            setFeedback('');
            setLoading(true);

            try {
                const response = await fetch(`/api/login/${currentRole}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email,
                        password
                    })
                });

                const rawData = await response.json().catch(() => null);
                const payload = normalizeResponse(rawData);

                if (!response.ok || !payload?.ok) {
                    const message = resolveErrorMessage(payload, response.status);
                    setFeedback(message);
                    return;
                }

                setFeedback('Authenticated successfully. Redirecting…', 'success');
                const redirectUrl = payload.redirect || '/dashboard';
                window.location.href = redirectUrl;
            } catch (error) {
                console.error('Login error:', error);
                setFeedback('We could not sign you in. Please try again in a moment.');
            } finally {
                setLoading(false);
            }
        }

        tabButtons.forEach((button) => {
            button.addEventListener('click', () => setRole(button.dataset.role || 'medico', button));
        });

        if (loginForm) {
            loginForm.addEventListener('submit', handleLogin);
        }

        if (forgotPasswordLink) {
            forgotPasswordLink.addEventListener('click', async (event) => {
                event.preventDefault();

                if (!emailInput) {
                    return;
                }

                const email = emailInput.value.trim();

                if (!email) {
                    setFeedback('Enter your email address so we can send the reset instructions.');
                    return;
                }

                setFeedback('');
                forgotPasswordLink.classList.add('loading');
                forgotPasswordLink.setAttribute('aria-busy', 'true');

                try {
                    const response = await fetch('/api/forgot-password', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ email })
                    });

                    if (response.ok) {
                        setFeedback('If your email is registered, you will receive reset instructions shortly.', 'success');
                    } else {
                        setFeedback('We could not start the reset process right now. Please try again later.');
                    }
                } catch (error) {
                    console.error('Forgot password error:', error);
                    setFeedback('We were unable to send reset instructions. Please try again later.');
                } finally {
                    forgotPasswordLink.classList.remove('loading');
                    forgotPasswordLink.removeAttribute('aria-busy');
                }
            });
        }

        if (googleLoginButton) {
            googleLoginButton.addEventListener('click', (event) => {
                event.preventDefault();
                setFeedback('Redirecting you to Google…', 'success');

                try {
                    window.location.href = `/api/login/google?role=${currentRole}`;
                } catch (error) {
                    console.error('Google login error:', error);
                    setFeedback('We could not connect to Google right now. Please try again in a moment.');
                }
            });
        }

        if (microsoftLoginButton) {
            microsoftLoginButton.addEventListener('click', (event) => {
                event.preventDefault();
                setFeedback('Redirecting you to Microsoft…', 'success');

                try {
                    window.location.href = `/api/login/microsoft?role=${currentRole}`;
                } catch (error) {
                    console.error('Microsoft login error:', error);
                    setFeedback('We could not connect to Microsoft right now. Please try again in a moment.');
                }
            });
        }
    });
})();
