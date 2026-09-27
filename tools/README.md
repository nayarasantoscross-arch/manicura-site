# Ferramentas do site

- `tailwind.input.css` → gera `css/site.css` (CSS pronto, no lugar do Tailwind via CDN). Rodar depois de mudar classes em qualquer página:
  `npx -y tailwindcss@3.4.17 -i tools/tailwind.input.css -o css/site.css --content "./*.html,./tools/*.py" --minify`
- `gerar_og.py` → miniaturas de compartilhamento (1200x630) em `img/og/`: `python tools/gerar_og.py`
- `catalogo_estatico.py` → grava as peças de `semijoias/catalogo.json` direto no HTML de `semijoias-jundiai.html`
  (para Google e IAs). Rodar sempre que o catálogo mudar: `python tools/catalogo_estatico.py`
- `servicos_do_app.py` → grava em `servicos-jundiai.html` (tabela, FAQ, JSON-LD) e no `llms.txt` os serviços
  liberados para agendamento online no app (vitrine pública `/api/reservar/salao/...`); ajusta o `priceRange`
  literal das páginas e lista pendências (textos fora da vitrine). Rodar sempre que serviço/preço mudar no app:
  `python tools/servicos_do_app.py` (`--duracao` mostra a duração; `--arquivo v.json` para teste offline)
