"""Publica no site os artigos do blog agendados cuja data já chegou.

Rascunhos ficam FORA do repo (não vazam antes da hora), em
C:/Users/Usuario/Downloads/Projects/_vps/blog/agendados/:
  <slug>.html  página completa, pronta
  <slug>.json  {"slug", "data": "AAAA-MM-DD", "categoria", "titulo_card", "resumo_card",
                "img_card", "img_alt", "llms", "remover_card_href"?: "#tpo-em-breve"}
Imagens e og ficam no repo desde já (img/site, img/og) — sem link, não aparecem.

Para cada artigo com data <= hoje e ainda não publicado: copia a página para a raiz,
põe o card no topo do blog, entra no sitemap e no llms.txt, commit e push (origin + vps).
Uso: python tools/publicar_agendados.py [--hoje AAAA-MM-DD] [--seco]
"""
import argparse, datetime as dt, html, json, re, shutil, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
AG = Path(r"C:/Users/Usuario/Downloads/Projects/_vps/blog/agendados")
LOG = AG.parent / "publicados.json"
SITE = "https://manicuraexpressnails.com"
GRADE = '<div class="grid md:grid-cols-2 gap-8">'


def card(m):
    e = html.escape
    return f'''
      <article class="bg-white rounded-3xl p-6 border border-[#D1BFA7]/50 flex flex-col gap-4">
       <div class="w-full h-64 rounded-2xl overflow-hidden shadow-lg"><a href="{m['slug']}.html"><img src="{e(m['img_card'])}" alt="{e(m['img_alt'])}" loading="lazy" class="w-full h-full object-cover object-center transition-transform duration-300 hover:scale-105"></a></div>
       <span class="text-[11px] font-subtitle tracking-[0.16em] uppercase text-[#B46342]">{e(m['categoria'])}</span>
       <h3 class="font-title text-xl tracking-wide"><a href="{m['slug']}.html" class="hover:text-[#B46342] transition-colors">{e(m['titulo_card'])}</a></h3>
       <p class="text-sm text-black/80 leading-relaxed">{e(m['resumo_card'])}</p>
       <a href="{m['slug']}.html" class="mt-auto text-xs font-subtitle text-[#B46342] hover:underline focus:outline-none focus-ring">Ler o artigo →</a>
      </article>
'''


def remover_article_com(txt, alvo):
    """Remove o <article> do blog que contém `alvo` (ex.: o card 'Em breve' que o artigo substitui)."""
    i = txt.find(alvo)
    if i < 0:
        return txt
    a = txt.rfind("<article", 0, i)
    b = txt.find("</article>", i) + len("</article>")
    return txt[:a] + txt[b:] if a >= 0 and b > i else txt


def publicar(m, hoje, seco):
    slug = m["slug"]
    v = subprocess.run([sys.executable, str(R / "tools" / "verificar_fontes.py"), str(AG / f"{slug}.html")])
    if v.returncode != 0:
        raise SystemExit(f"{slug}: verificador de fontes falhou — NÃO publicado")
    for img in [m["img_card"]] + re.findall(r'src="(img/[^"]+)"', (AG / f"{slug}.html").read_text(encoding="utf-8")):
        if not (R / img).exists():
            raise SystemExit(f"{slug}: imagem ausente no repo: {img}")

    b = R / "blog-jundiai.html"
    t = b.read_text(encoding="utf-8")
    if f'href="{slug}.html"' not in t:
        if m.get("remover_card_href"):
            t = remover_article_com(t, m["remover_card_href"])
        t = t.replace(GRADE, GRADE + card(m), 1)
    s = R / "sitemap.xml"
    sx = s.read_text(encoding="utf-8")
    if f"/{slug}.html" not in sx:
        sx = sx.replace("</urlset>", f"  <url>\n    <loc>{SITE}/{slug}.html</loc>\n    <lastmod>{hoje}</lastmod>\n    <priority>0.85</priority>\n  </url>\n</urlset>")
    l = R / "llms.txt"
    lt = l.read_text(encoding="utf-8")
    if f"/{slug}.html" not in lt:
        linha = f"- [{m['titulo_card']}]({SITE}/{slug}.html): {m['llms']}\n"
        pos = lt.find("- [Contato](")
        lt = lt[:pos] + linha + lt[pos:] if pos >= 0 else lt + linha
    if seco:
        print(f"[seco] publicaria {slug}")
        return
    shutil.copyfile(AG / f"{slug}.html", R / f"{slug}.html")
    b.write_text(t, encoding="utf-8"); s.write_text(sx, encoding="utf-8"); l.write_text(lt, encoding="utf-8")
    print(f"publicado {slug}")


def git(*a):
    subprocess.run(["git", "-C", str(R), *a], check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--hoje", default=dt.date.today().isoformat())
    p.add_argument("--seco", action="store_true")
    a = p.parse_args()
    feitos = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}
    novos = []
    for j in sorted(AG.glob("*.json")):
        m = json.loads(j.read_text(encoding="utf-8"))
        if m["data"] <= a.hoje and m["slug"] not in feitos:
            publicar(m, a.hoje, a.seco)
            novos.append(m)
    if not novos:
        print("nada a publicar hoje", a.hoje)
        return
    if a.seco:
        return
    git("add", "-A", "--", "*.html", "sitemap.xml", "llms.txt", "img")
    git("commit", "-m", "blog: publica " + ", ".join(m["slug"] for m in novos) + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    git("push", "origin", "HEAD")
    git("push", "vps", "HEAD")
    for m in novos:
        feitos[m["slug"]] = a.hoje
    LOG.write_text(json.dumps(feitos, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
