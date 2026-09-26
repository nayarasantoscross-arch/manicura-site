"""Grava o catálogo de semijoias direto no HTML de semijoias-jundiai.html (para Google e robôs de IA,
que nem sempre executam JavaScript) + dados estruturados (ItemList de Product).

A página continua buscando o estoque AO VIVO na API do app e substitui esta lista ao carregar;
aqui não vai status de estoque (ficaria velho). Rodar sempre que semijoias/catalogo.json mudar:
    python tools/catalogo_estatico.py
"""
import html, json, re, urllib.parse
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "semijoias-jundiai.html"
URL = "https://manicuraexpressnails.com/semijoias-jundiai.html"
WHATS = "5511959963541"
ORDEM = ["Brincos", "Anéis", "Colares & Chokers", "Pulseiras & Braceletes", "Pingentes", "Conjuntos", "Piercings", "Acessórios"]
INI, FIM = "<!--catalogo-estatico:inicio-->", "<!--catalogo-estatico:fim-->"
LD_INI, LD_FIM = "<!--ld-catalogo:inicio-->", "<!--ld-catalogo:fim-->"


def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def card(p):
    e = lambda s: html.escape(str(s), quote=True)
    msg = f"Olá! Tenho interesse na semijoia {p['nome']} (cód. {p['codigo']}) que vi no catálogo Gift Moment."
    if p["fotos"]:
        foto = (f'<div class="foto-trilho"><img loading="lazy" src="semijoias/img/{e(p["fotos"][0])}" '
                f'alt="{e(p["nome"])}"></div>')
    else:
        foto = ('<div class="h-full flex flex-col items-center justify-center text-center text-black/40 text-xs '
                'font-subtitle gap-1"><span class="text-2xl">✨</span>Foto em breve</div>')
    return (f'<article id="p-{e(p["codigo"])}" class="bg-white rounded-2xl border border-[#D1BFA7]/50 overflow-hidden flex flex-col">'
            f'<div class="card-foto relative bg-white">{foto}</div>'
            '<div class="p-3 md:p-4 flex flex-col gap-1 flex-1">'
            f'<h3 class="font-subtitle text-sm leading-snug">{e(p["nome"])}</h3>'
            f'<p class="text-[11px] text-black/40">cód. {e(p["codigo"])}</p>'
            f'<p class="mt-1 font-title text-lg text-[#8E4A2C]">{brl(p["preco"])}</p>'
            f'<p class="text-xs text-black/60">ou 3x de {brl(p["parcela3x"])} sem juros no cartão</p>'
            f'<a href="https://wa.me/{WHATS}?text={urllib.parse.quote(msg)}" target="_blank" rel="noopener noreferrer" class="mt-auto pt-3">'
            '<span class="w-full inline-flex items-center justify-center px-3 py-2 rounded-full bg-[#B46342] text-white text-xs '
            'font-subtitle tracking-wide hover:bg-[#8E4A2C] transition-colors">Quero esta peça</span></a>'
            "</div></article>")


def main():
    pecas = json.loads((RAIZ / "semijoias" / "catalogo.json").read_text("utf-8"))
    pecas.sort(key=lambda p: (ORDEM.index(p["categoria"]) if p["categoria"] in ORDEM else 99, p["preco"]))
    s = open(PAGINA, encoding="utf-8", newline="").read()  # preserva os fins de linha (CRLF/LF) do arquivo

    cards = "\n".join(card(p) for p in pecas)
    bloco = f"{INI}\n{cards}\n{FIM}"
    if INI in s:
        s = re.sub(re.escape(INI) + r".*?" + re.escape(FIM), lambda _: bloco, s, count=1, flags=re.S)
    else:
        s, n = re.subn(r'(<div id="grade"[^>]*>)\s*<p class="col-span-full[^"]*">Carregando as peças…</p>',
                       lambda m: m.group(1) + "\n" + bloco, s, count=1)
        assert n == 1, "não achei a grade com 'Carregando as peças…'"

    itens = []
    for i, p in enumerate(pecas, 1):
        prod = {"@type": "Product", "name": p["nome"], "sku": p["codigo"], "category": p["categoria"],
                "brand": {"@type": "Brand", "name": "Gift Moment"}, "url": f"{URL}#p-{p['codigo']}",
                "offers": {"@type": "Offer", "price": f"{p['preco']:.2f}", "priceCurrency": "BRL",
                           "url": f"{URL}#p-{p['codigo']}",
                           "seller": {"@id": "https://manicuraexpressnails.com/#estudio"}}}
        if p["fotos"]:
            prod["image"] = f"https://manicuraexpressnails.com/semijoias/img/{p['fotos'][0]}"
        itens.append({"@type": "ListItem", "position": i, "item": prod})
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "Catálogo de semijoias Gift Moment",
          "url": URL, "numberOfItems": len(itens), "itemListElement": itens}
    ld_bloco = f'{LD_INI}<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>{LD_FIM}'
    if LD_INI in s:
        s = re.sub(re.escape(LD_INI) + r".*?" + re.escape(LD_FIM), lambda _: ld_bloco, s, count=1, flags=re.S)
    else:
        s = s.replace("</head>", "  " + ld_bloco + "\n</head>", 1)

    open(PAGINA, "w", encoding="utf-8", newline="").write(s)
    print(f"ok: {len(pecas)} peças gravadas no HTML")


if __name__ == "__main__":
    main()
