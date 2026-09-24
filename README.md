# manicuraexpressnails.com — site estático (Hostinger)

Fonte da verdade do site. **Nunca editar direto na Hostinger** — edita aqui, commit, publica.

## Os 3 lugares
| Lugar | Caminho |
|---|---|
| PC | `C:\Users\Usuario\Downloads\Projects\manicura-site` |
| GitHub | `nayarasantoscross-arch/manicura-site` |
| VPS | `/opt/manicura-site` (publica na Hostinger via FTP; credenciais em `/app/manicura_express/.env`) |

## Publicar
```bash
# no PC
git add -A && git commit -m "..." && git push origin main
# na VPS
cd /opt/manicura-site && git pull
python3 deploy/publicar.py --rascunho      # confere em https://manicuraexpressnails.com/_rascunhos/site/
python3 deploy/publicar.py --producao      # só depois do ok (faz backup do que sobrescreve)
```

## Catálogo de semijoias (`semijoias-jundiai.html`)
- Preço e **estoque vêm ao vivo** do app: `GET https://app.manicuraexpressnails.com/api/vitrine/semijoias`
  (estoque > 0 → "Disponível"; 0 → "Sob encomenda"). Venda fechada na comanda baixa o estoque sozinha.
- `semijoias/catalogo.json` + `semijoias/img/` = fotos (principal + extras) e reserva se a API cair.
- Gerados por `gift-moment-semijoias/gerar_site.py` (fora deste repo). Foto nova de uma peça:
  `semijoias/img/<código>-<nome>.webp` + ajustar `catalogo.json` (e `photo_url` do produto no app).
