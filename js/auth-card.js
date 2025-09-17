(function () {
    'use strict';

    const scriptElement = document.currentScript;

    document.addEventListener('DOMContentLoaded', () => {
        const tabButtons = document.querySelectorAll('.tab-button');
        const loginForm = document.querySelector('.login-form');
        const loginButton = document.querySelector('#login-btn');
        const loginButtonText = loginButton?.querySelector('.button-text');
        const loginSpinner = loginButton?.querySelector('.loading-spinner');
        const feedbackMessage = document.querySelector('#feedback-message');
        const emailInput = document.querySelector('#email');
        const passwordInput = document.querySelector('#password');
        const forgotPasswordLink = document.querySelector('#forgot-password');
        const googleLoginButton = document.querySelector('#google-login');
        const microsoftLoginButton = document.querySelector('#microsoft-login');
        const activeTab = document.querySelector('.tab-button.active');

        const defaultRedirect = scriptElement?.dataset.redirect || document.body?.dataset.redirect || '/dashboard';

        const errorMessages = {
            INVALID_CREDENTIALS: 'We could not find an account with those credentials.',
            INVALID_EMAIL_FORMAT: 'Please enter a valid email address.',
            EMAIL_PASSWORD_REQUIRED: 'Email and password are required.',
            ACCOUNT_LOCKED: 'Too many failed attempts. Please try again in a few minutes.',
            JSON_REQUIRED: 'Something went wrong with the request. Please try again.',
            INVALID_ROLE: 'The selected role is not available for this account.',
            INVALID_DATA: 'We need both email and password to sign you in.',
            MISSING_FIELDS: 'Please enter your email address and password.',
        };

        let currentRole = activeTab?.dataset.role || 'medico';

        function updateRole(button) {
            const nextRole = button?.dataset.role;
            if (!nextRole) {
                return;
            }

            currentRole = nextRole;

            tabButtons.forEach((tab) => {
                const isActive = tab === button;
                tab.classList.toggle('active', isActive);
                tab.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });
        }

        function setFeedback(message, type = 'error') {
            if (!feedbackMessage) {
                return;
            }

            if (!message) {
                feedbackMessage.textContent = '';
                feedbackMessage.style.display = 'none';
                feedbackMessage.classList.remove('feedback-error', 'feedback-success');
                return;
            }

            feedbackMessage.textContent = message;
            feedbackMessage.style.display = 'block';
            feedbackMessage.classList.toggle('feedback-success', type === 'success');
            feedbackMessage.classList.toggle('feedback-error', type !== 'success');
        }

        function toggleLoading(isLoading) {
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

        function normalizePayload(data) {
            if (Array.isArray(data)) {
                return data[0];
            }
            return data;
        }

        function resolveError(payload, statusCode) {
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

            if (payload.message) {
                return payload.message;
            }

            return 'Unable to sign in. Please check your credentials and try again.';
        }

        function toggleForgotLoading(isLoading) {
            if (!forgotPasswordLink) {
                return;
            }

            forgotPasswordLink.classList.toggle('loading', isLoading);
            if (isLoading) {
                forgotPasswordLink.setAttribute('aria-busy', 'true');
            } else {
                forgotPasswordLink.removeAttribute('aria-busy');
            }
        }

        async function handleLogin(event) {
            event?.preventDefault();

            const email = emailInput?.value.trim() || '';
            const password = passwordInput?.value.trim() || '';

            if (!email || !password) {
                setFeedback('Please enter your email and password to continue.');
                emailInput?.focus();
                return;
            }

            setFeedback('');
            toggleLoading(true);

            try {
                const response = await fetch(`/api/login/${encodeURIComponent(currentRole)}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email, password }),
                });

                const payload = normalizePayload(await response.json().catch(() => null));

                if (!response.ok || !payload?.ok) {
                    const message = resolveError(payload, response.status);
                    setFeedback(message);
                    return;
                }

                setFeedback('Authenticated successfully. Redirecting…', 'success');

                const redirectTarget = payload.redirect || defaultRedirect;
                window.setTimeout(() => {
                    window.location.href = redirectTarget;
                }, 300);
            } catch (error) {
                console.error('Login error:', error);
                setFeedback('We could not sign you in. Please try again in a moment.');
            } finally {
                toggleLoading(false);
            }
        }

        tabButtons.forEach((button) => {
            button.addEventListener('click', () => {
                updateRole(button);
                setFeedback('');
            });
        });

        if (loginForm) {
            loginForm.addEventListener('submit', handleLogin);
        }

        if (forgotPasswordLink) {
            forgotPasswordLink.addEventListener('click', async (event) => {
                event.preventDefault();

                const email = emailInput?.value.trim() || '';

                if (!email) {
                    setFeedback('Enter your email address so we can send the reset instructions.');
                    emailInput?.focus();
                    return;
                }

                setFeedback('');
                toggleForgotLoading(true);

                try {
                    const response = await fetch('/api/forgot-password', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ email }),
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
                    toggleForgotLoading(false);
                }
            });
        }

        function attachSocial(button, provider, providerLabel) {
            if (!button) {
                return;
            }

            button.addEventListener('click', (event) => {
                event.preventDefault();
                setFeedback(`Redirecting you to ${providerLabel}…`, 'success');

                const overrideUrl = button.dataset.url;
                let url = overrideUrl
                    ? overrideUrl.replace('{role}', encodeURIComponent(currentRole))
                    : `/api/login/${provider}?role=${encodeURIComponent(currentRole)}`;

                if (!overrideUrl && button.dataset.appendRole === 'false') {
                    url = `/api/login/${provider}`;
                }

                try {
                    window.location.href = url;
                } catch (error) {
                    console.error(`${providerLabel} login error:`, error);
                    setFeedback(`We could not connect to ${providerLabel} right now. Please try again in a moment.`);
                }
            });
        }

        attachSocial(googleLoginButton, 'google', 'Google');
        attachSocial(microsoftLoginButton, 'microsoft', 'Microsoft');
    });
})();
