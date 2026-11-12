// Tokens do design Evidēns (home e check-up).
// O CSS publicado (static/evidens.css) é gerado a partir deste arquivo e de
// static/evidens.src.css — ver docs/deploy.md, seção "CSS".
module.exports = {
  content: ['./index.html', './intelligent-tools.html', './contact.html'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter Tight"', 'ui-sans-serif', 'system-ui'],
        serif: ['"Instrument Serif"', 'ui-serif', 'Georgia'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        ink: '#14292F',
        teal: { DEFAULT: '#0E97B5', dark: '#0B7A93' },
        aqua: '#8FD6E0',
        mist: '#DCEBEE',
        paper: '#F6F7F4',
        sand: '#F3EDDC',
      },
      letterSpacing: { tightest: '-0.045em' },
    },
  },
  plugins: [],
};
