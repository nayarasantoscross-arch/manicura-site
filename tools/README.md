# Ferramentas do site

- `tailwind.input.css` → gera `css/site.css` (CSS pronto, no lugar do Tailwind via CDN). Rodar depois de mudar classes em qualquer página:
  `npx -y tailwindcss@3.4.17 -i tools/tailwind.input.css -o css/site.css --content "./*.html,./tools/*.py" --minify`
- `catalogo_estatico.py` → grava as peças de `semijoias/catalogo.json` direto no HTML de `semijoias-jundiai.html`
  (para Google e IAs). Rodar sempre que o catálogo mudar: `python tools/catalogo_estatico.py`
