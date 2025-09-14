# Deploy via GitHub Pages

1. Vá em Settings > Pages.
2. Em "Build and deployment", selecione "GitHub Actions".
3. Faça merge na branch padrão; a action `Deploy static site to GitHub Pages` fará o publish automático.
4. Para disparar manualmente, acesse Actions > `Deploy static site to GitHub Pages` > Run workflow.
5. O status e a URL pública aparecem no ambiente `github-pages` do repositório.

Notas
- O workflow publica a partir da raiz do repo (.) onde estão `index.html` e `analytics.html`.
- Se desejar publicar a partir de `src/static`, altere `with.path` para `src/static` no job `Upload artifact`.