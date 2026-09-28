"""Grava na página de serviços (servicos-jundiai.html) e no llms.txt EXATAMENTE os serviços liberados para
agendamento online no app — nada de tabela escrita à mão.

Fonte da verdade: a vitrine pública do app
    GET https://app.manicuraexpressnails.com/api/reservar/salao/manicura-express-nails
(JSON com unit, services, categories, ...). As categorias vêm numeradas ("1. Esmalte Gel UV"): a página
mostra sem o "N. ", mas ordena por ele.

O que é regerado (sempre o bloco inteiro, então rodar 2x dá o mesmo resultado):
  - servicos-jundiai.html, entre <!-- servicos:inicio --> e <!-- servicos:fim -->: a tabela por categoria
    (um preço por serviço; o app não tem preço Pix separado). priceMax != price → "a partir de R$ X";
    preço 0 → "Sob consulta". Duração só com --duracao (a do app é a do bloco de agenda e ainda conflita
    com o slogan "30 minutos" — decisão pendente da dona).
  - servicos-jundiai.html, entre <!-- faq:inicio --> e <!-- faq:fim -->: o FAQ visível; e os JSON-LD
    (hasOfferCatalog do NailSalon + FAQPage) reescritos a partir dos mesmos dados.
  - llms.txt, entre <!-- servicos:inicio --> e <!-- servicos:fim -->.
  - priceRange literal ("R$ a - R$ b") no JSON-LD de qualquer página: min–max real da vitrine (ignora 0).

Textos de marketing fora dos marcadores NÃO são tocados: o script só os lista como pendências
(serviços que não estão na vitrine, preços divergentes, duração x slogan).

Uso:
    python tools/servicos_do_app.py                 # baixa a vitrine do app
    python tools/servicos_do_app.py --arquivo v.json # lê um JSON local (teste offline)
    python tools/servicos_do_app.py --duracao        # mostra a coluna de duração
"""
import argparse, html, json, re, sys, urllib.request
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "servicos-jundiai.html"
LLMS = RAIZ / "llms.txt"
URL_VITRINE = "https://app.manicuraexpressnails.com/api/reservar/salao/manicura-express-nails"
URL_PAGINA = "https://manicuraexpressnails.com/servicos-jundiai.html"
ESTUDIO = "https://manicuraexpressnails.com/#estudio"
AGENDAR = "https://expressnails.belasis.app"  # o link que a página já usa nos botões "Agendar"
WHATS = "(11) 95996-3541"
INI, FIM = "<!-- servicos:inicio -->", "<!-- servicos:fim -->"
FAQ_INI, FAQ_FIM = "<!-- faq:inicio -->", "<!-- faq:fim -->"
AVISO = "<!-- gerado por tools/servicos_do_app.py a partir da vitrine do app; não editar à mão -->"
# Textos institucionais das categorias (vêm da página antiga; o app não tem descrição de categoria).
INTRO = {
    "Esmalte Gel UV": "Durabilidade impecável com brilho espelhado. Utilizamos apenas produtos premium para a saúde das suas unhas.",
    "Esmalte Tradicional": "Para as amantes do clássico, uma linha completa de esmaltes e removedores de formulação suave.",
    "Masculino": "Cuidado e bem-estar também para eles.",
}
# Página dedicada de cada categoria (link logo abaixo do título da categoria).
PAGINA_CAT = {
    "Esmalte Gel UV": ("esmaltacao-em-gel-jundiai.html", "Esmaltação em gel em Jundiaí: como funciona e perguntas frequentes"),
    "Esmalte Tradicional": ("pedicure-jundiai.html", "Pedicure em Jundiaí: preços, biossegurança e perguntas frequentes"),
    "Alongamento": ("alongamento-de-unhas-jundiai.html", "Alongamento de unhas em Jundiaí: como funciona e manutenção"),
    "Reconstrução Unhas/Cantos": ("pedicure-jundiai.html", "Reconstrução de unhas/cantos na pedicure"),
}
FAQ_GEL = "Manicure Gel UV"  # serviço citado no FAQ de preço/duração
# Erros de digitação conhecidos nos nomes do app (corrigir NO APP; aqui só avisa).
SUSPEITOS = [(r"\bEsmata", "Esmalta…"), (r"\bConsultar\s+Art", "Consultar Artística → Consultoria Artística?")]

BTN = ('<a href="{link}" target="_blank" rel="noopener" class="inline-block text-center px-5 py-2 rounded-full '
       'bg-[#B46342] text-white text-xs font-subtitle tracking-wide hover:bg-[#8E4A2C] transition-colors '
       'focus:outline-none focus-ring whitespace-nowrap">Agendar</a>')
e = lambda s: html.escape(str(s), quote=True)


# ---------------------------------------------------------------- dados

def baixar(arquivo):
    if arquivo:
        return json.loads(Path(arquivo).read_text("utf-8-sig"))
    req = urllib.request.Request(URL_VITRINE, headers={"User-Agent": "manicura-site/servicos_do_app", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def nome_limpo(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def categoria(nome):
    """'1. Esmalte Gel UV' → (1, 'Esmalte Gel UV'); sem número → (999, nome)."""
    m = re.match(r"\s*(\d+)\s*\.\s*(.*)", nome or "")
    return (int(m.group(1)), nome_limpo(m.group(2))) if m else (999, nome_limpo(nome))


def dec(v):
    return Decimal(str(v if v not in (None, "") else "0"))


def carregar(dados):
    servicos, cats = dados.get("services") or [], dados.get("categories") or []
    if not servicos:
        sys.exit("ERRO: a vitrine veio sem serviços — nada foi alterado.")
    por_id = {c["id"]: categoria(c["name"]) for c in cats}
    grupos = {}
    for s in servicos:  # mantém a ordem do app dentro de cada categoria
        ordem, cat = por_id.get(s.get("categoryId"), (9999, "Outros serviços"))
        preco, preco_max = dec(s.get("price")), dec(s.get("priceMax") if s.get("priceMax") not in (None, "") else s.get("price"))
        dur = int(s.get("durationMinutes") or 0)
        grupos.setdefault((ordem, cat), []).append({
            "nome": nome_limpo(s["name"]), "nome_app": s["name"], "preco": preco, "preco_max": max(preco, preco_max),
            "dur": dur, "dur_max": max(dur, int(s.get("durationMax") or dur)),
            "descricao": nome_limpo(s.get("description")) or None,
        })
    return [(cat, grupos[k]) for k in sorted(grupos) for cat in [k[1]]]


# ---------------------------------------------------------------- formatação

def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl_curto(v):  # para priceRange: "R$ 20", "R$ 20,50"
    return "R$ " + (f"{int(v)}" if v == int(v) else f"{v:.2f}".replace(".", ","))


def preco_txt(s):
    if s["preco"] == 0 and s["preco_max"] == 0:
        return "Sob consulta"
    if s["preco_max"] != s["preco"]:
        return f"a partir de {brl(s['preco'])}"
    return brl(s["preco"])


def hm(m):
    return f"{m // 60}h{m % 60:02d}"


def dur_txt(s):
    return hm(s["dur"]) if s["dur_max"] == s["dur"] else f"{hm(s['dur'])} a {hm(s['dur_max'])}"


def slug(t):
    t = t.lower()
    for a, b in zip("áàâãéêíóôõúüç", "aaaaeeiooouuc"):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


# ---------------------------------------------------------------- blocos gerados

def html_tabela(grupos, duracao, link):
    L = [f"      {INI}", f"      {AVISO}"]
    for i, (cat, itens) in enumerate(grupos):
        sid = f"cat-{slug(cat)}-title"
        if i:
            L.append("")
        L += [f'      <section aria-labelledby="{sid}" class="bg-white rounded-3xl p-6 md:p-8 border border-[#D1BFA7]/50">',
              '       <div class="mb-6">',
              f'        <h2 id="{sid}" class="font-subtitle text-xl tracking-wide mb-2">{e(cat)}</h2>']
        if cat in INTRO:
            L.append(f'        <p class="text-sm text-black/70">{e(INTRO[cat])}</p>')
        if cat in PAGINA_CAT:
            href, txt = PAGINA_CAT[cat]
            L.append(f'        <p class="text-sm mt-2"><a class="text-[#B46342] underline" href="{href}">{e(txt)}</a></p>')
        L += ["       </div>", '       <div class="space-y-4">']
        for s in itens:
            desc = f'<p class="text-sm text-black/70">{e(s["descricao"])}</p>' if s["descricao"] else ""
            L += ['        <article class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl bg-[#FBF5EE] border border-[#D1BFA7]/30">',
                  f'         <div class="flex-1"><h3 class="font-subtitle text-base tracking-wide mb-1">{e(s["nome"])}</h3>{desc}</div>',
                  '         <div class="flex flex-wrap items-center gap-x-4 gap-y-3 md:gap-6">',
                  f'          <div class="text-center"><p class="text-lg font-subtitle text-[#B46342]">{e(preco_txt(s))}</p><p class="text-xs text-black/60">Preço</p></div>']
            if duracao:
                L.append(f'          <div class="text-center"><p class="text-lg font-subtitle">{dur_txt(s)}</p><p class="text-xs text-black/60">Duração</p></div>')
            L += [f"          {BTN.format(link=e(link))}", "         </div>", "        </article>"]
        L += ["       </div>", "      </section>"]
    L.append(f"      {FIM}")
    return L


def acha(grupos, nome):
    return next((s for _, itens in grupos for s in itens if s["nome"].lower() == nome.lower()), None)


def perguntas(grupos, duracao, link):
    """FAQ único → vira o HTML visível e o FAQPage do JSON-LD. Preço/duração saem da vitrine."""
    q = []
    gel = acha(grupos, FAQ_GEL)
    if gel and preco_txt(gel) != "Sob consulta":
        q.append(("Quanto custa a manicure com esmaltação em gel em Jundiaí?",
                  f"Na Manicura Express Nails, a {gel['nome']} custa {preco_txt(gel)}. A tabela completa, com todos os serviços "
                  "disponíveis para agendamento online, está nesta página."))
    if duracao and gel:
        q.append(("Quanto tempo demora a manicure com esmalte em gel?",
                  f"Na agenda, a {gel['nome']} ocupa {dur_txt(gel)}. A duração de cada serviço aparece na tabela desta página."))
    q.append(("Quanto tempo dura a esmaltação em gel?",
              "Com os cuidados certos, a esmaltação em gel tem até 21 dias de durabilidade."))
    q.append(("Quais são as formas de pagamento?",
              "Cartão, Pix ou dinheiro. Os preços desta tabela são os mesmos do agendamento online."))
    q.append(("Como agendar um horário?",
              f"Pelo agendamento online em {re.sub(r'^https?://', '', link).rstrip('/')} ou pelo WhatsApp {WHATS}. "
              "Atendemos de segunda a sexta, das 9h às 12h e das 13h às 19h30, e aos sábados, das 8h às 12h."))
    return q


def html_faq(q, duracao):
    L = [f"      {FAQ_INI}",
         '      <section aria-labelledby="faq-servicos-title" class="bg-white rounded-3xl p-6 md:p-8 border border-[#D1BFA7]/50">',
         '       <div class="mb-6">',
         '        <h2 id="faq-servicos-title" class="font-subtitle text-xl tracking-wide mb-2">Perguntas frequentes</h2>',
         f'        <p class="text-sm text-black/70">{"Preço, duração, pagamento" if duracao else "Preço, pagamento"} e agendamento.</p>',
         "       </div>", "       <div>"]
    for p, r in q:
        L.append(f'         <details class="py-3 border-t border-[#D1BFA7]/30"><summary class="font-subtitle text-base tracking-wide cursor-pointer">{e(p)}</summary><p class="mt-2 text-sm text-black/80 leading-relaxed">{e(r)}</p></details>')
    L += ["       </div>", "      </section>", f"      {FAQ_FIM}"]
    return L


def ld_catalogo(grupos):
    cats = []
    for cat, itens in grupos:
        ofertas = []
        for s in itens:
            o = {"@type": "Offer",
                 "itemOffered": {"@type": "Service", "name": s["nome"], "category": cat, "provider": {"@id": ESTUDIO}}}
            if s["preco"] > 0 or s["preco_max"] > 0:
                o["price"] = f"{s['preco']:.2f}"
                o["priceCurrency"] = "BRL"
                if s["preco_max"] != s["preco"]:
                    o["priceSpecification"] = {"@type": "PriceSpecification", "minPrice": f"{s['preco']:.2f}",
                                               "maxPrice": f"{s['preco_max']:.2f}", "priceCurrency": "BRL"}
            o["url"] = URL_PAGINA
            ofertas.append(o)
        cats.append({"@type": "OfferCatalog", "name": cat, "itemListElement": ofertas})
    return {"@type": "OfferCatalog", "name": "Serviços e preços — Manicura Express Nails, Jundiaí",
            "url": URL_PAGINA, "itemListElement": cats}


def ld_faq(q):
    return {"@context": "https://schema.org", "@type": "FAQPage", "@id": URL_PAGINA + "#faq",
            "mainEntity": [{"@type": "Question", "name": p, "acceptedAnswer": {"@type": "Answer", "text": r}} for p, r in q]}


def llms_bloco(grupos, duracao):
    L = [INI, "## Serviços e preços (os mesmos do agendamento online)", ""]
    for cat, itens in grupos:
        L.append(f"### {cat}")
        for s in itens:
            extra = f" ({dur_txt(s)} na agenda)" if duracao else ""
            L.append(f"- {s['nome']}: {preco_txt(s)}{extra}")
        L.append("")
    L += [f"Tabela completa: {URL_PAGINA}", FIM]
    return L


# ---------------------------------------------------------------- escrita

def eol_de(s):
    return "\r\n" if s.count("\r\n") * 2 > s.count("\n") else "\n"


def troca_marcado(s, ini, fim, linhas, eol, primeira_vez):
    bloco = eol.join(linhas)
    padrao = r"[ \t]*" + re.escape(ini) + r".*?" + re.escape(fim)
    if re.search(padrao, s, flags=re.S):
        return re.sub(padrao, lambda _: bloco, s, count=1, flags=re.S)
    return primeira_vez(s, bloco)


def migra_tabela(s, bloco):
    """1ª execução: troca as seções escritas à mão (do início da grade até o FAQ) pelo bloco marcado."""
    a = s.index('<div class="space-y-12">')
    a = s.index("\n", a) + 1
    b = s.index('<section aria-labelledby="faq-servicos-title"', a)
    b = s.rindex("\n", 0, b) + 1
    eol = eol_de(s)
    return s[:a] + bloco + eol + s[b:]


def migra_faq(s, bloco):
    a = s.index('<section aria-labelledby="faq-servicos-title"')
    a = s.rindex("\n", 0, a) + 1
    b = s.index("</section>", a) + len("</section>")
    return s[:a] + bloco + s[b:]


def reescreve_ld(s, eol, muda):
    """Aplica `muda(obj)` em cada <script type="application/ld+json"> (retorna obj novo ou None = não mexe)."""
    def sub(m):
        corpo = m.group(2)
        obj = json.loads(corpo)
        novo = muda(obj)
        if novo is None:
            return m.group(0)
        pre = re.match(r"\s*", corpo).group(0)
        pos = re.search(r"\s*$", corpo).group(0)
        return m.group(1) + pre + json.dumps(novo, ensure_ascii=False, indent=2).replace("\n", eol) + pos + m.group(3)
    return re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', sub, s, flags=re.S)


def ler(p):
    return open(p, encoding="utf-8", newline="").read()  # preserva CRLF/LF


def gravar(p, s):
    if ler(p) != s:
        open(p, "w", encoding="utf-8", newline="").write(s)
        return True
    return False


def faixa(grupos):
    ps = [v for _, itens in grupos for s in itens for v in (s["preco"], s["preco_max"]) if v > 0]
    return f"{brl_curto(min(ps))} - {brl_curto(max(ps))}"


# ---------------------------------------------------------------- pendências (só relata)

def sem_tags(linha):
    return re.sub(r"<[^>]+>", " ", linha)


def fora_dos_marcadores(s):
    for ini, fim in ((INI, FIM), (FAQ_INI, FAQ_FIM)):
        s = re.sub(re.escape(ini) + r".*?" + re.escape(fim), lambda m: "\n" * m.group(0).count("\n"), s, flags=re.S)
    return s


def pendencias(grupos, dados):
    precos = {s["preco"] for _, itens in grupos for s in itens} | {s["preco_max"] for _, itens in grupos for s in itens}
    out = []
    for s in dados.get("services") or []:
        n = s["name"]
        if re.search(r"\s{2,}", n):
            out.append(f"[app] nome com espaço duplo: {n!r} (site mostra normalizado)")
        if re.match(r"\s*\d+\.\s", n):
            out.append(f"[app] nome de SERVIÇO com numeração de categoria: {n!r}")
        for rx, dica in SUSPEITOS:
            if re.search(rx, n):
                out.append(f"[app] provável erro de digitação: {n!r} ({dica})")
    gel = acha(grupos, FAQ_GEL)
    achados = {}  # (tipo, texto) → ["arquivo:linha", ...] — o mesmo texto repetido em várias páginas vira 1 item
    def nota(tipo, onde, texto):
        achados.setdefault((tipo, texto), []).append(onde)
    for p in sorted(RAIZ.glob("*.html")) + [LLMS]:
        if p.name.startswith("semijoias"):
            continue
        for i, linha in enumerate(fora_dos_marcadores(ler(p)).splitlines(), 1):
            if '"priceRange"' in linha:
                continue
            txt = re.sub(r"\s+", " ", sem_tags(linha)).strip()
            onde = f"{p.name}:{i}"
            for m in re.finditer(r"R\$\s?(\d{1,4}(?:,\d{2})?)", txt):
                if Decimal(m.group(1).replace(",", ".")) not in precos:
                    nota("preço fora da vitrine", onde, f"{m.group(0)} — {txt[:140]}")
            if re.search(r"(?i)shiatsu|\bpacotes? (promocion|\d|de \d)", txt):
                nota("serviço fora da vitrine (Shiatsu/pacote)", onde, txt[:140])
            if gel and re.search(r"(?i)\b30 ?min", txt):
                nota(f"duração: promete 30 min; vitrine {gel['nome']} = {dur_txt(gel)}", onde, txt[:120])
            if re.search(r"(?i)garantid[oa]", txt):
                nota("texto diz 'garantido'", onde, txt[:140])
    for (tipo, texto), onde in achados.items():
        out.append(f"[{tipo}] {', '.join(onde)} — {texto}")
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--arquivo", help="ler a vitrine de um JSON local em vez de baixar")
    ap.add_argument("--duracao", action="store_true", help="mostrar a duração (do bloco de agenda do app)")
    ap.add_argument("--link-agendar", default=AGENDAR, help=f"link dos botões Agendar (padrão: {AGENDAR})")
    ap.add_argument("--sem-pendencias", action="store_true", help="não listar pendências")
    a = ap.parse_args()

    dados = baixar(a.arquivo)
    grupos = carregar(dados)
    q = perguntas(grupos, a.duracao, a.link_agendar)
    mudou = []

    # 1) servicos-jundiai.html
    s = ler(PAGINA)
    eol = eol_de(s)
    s = troca_marcado(s, INI, FIM, html_tabela(grupos, a.duracao, a.link_agendar), eol, migra_tabela)
    s = troca_marcado(s, FAQ_INI, FAQ_FIM, html_faq(q, a.duracao), eol, migra_faq)

    def muda_pagina(obj):
        if obj.get("@type") == "FAQPage":
            return ld_faq(q)
        if "hasOfferCatalog" in obj:
            obj = dict(obj)
            obj["hasOfferCatalog"] = ld_catalogo(grupos)
            return obj
        return None
    s = reescreve_ld(s, eol, muda_pagina)
    if gravar(PAGINA, s):
        mudou.append(PAGINA.name)

    # 2) llms.txt
    t = ler(LLMS)
    def migra_llms(t, bloco):
        a_ = t.index("## Serviços principais")
        b_ = t.index("## Diferenciais", a_)
        return t[:a_] + bloco + eol_de(t) * 2 + t[b_:]
    t = troca_marcado(t, INI, FIM, llms_bloco(grupos, a.duracao), eol_de(t), migra_llms)
    if gravar(LLMS, t):
        mudou.append(LLMS.name)

    # 3) priceRange literal (R$ ...) em qualquer página
    fx = faixa(grupos)
    for p in sorted(RAIZ.glob("*.html")):
        h = ler(p)
        h2 = re.sub(r'("priceRange":\s*")R\$[^"]*(")', lambda m: m.group(1) + fx + m.group(2), h)
        if gravar(p, h2) and p.name not in mudou:
            mudou.append(p.name)

    n = sum(len(i) for _, i in grupos)
    print(f"ok: {n} serviços em {len(grupos)} categorias; priceRange {fx}; duração {'VISÍVEL' if a.duracao else 'oculta'}")
    print("alterados: " + (", ".join(mudou) if mudou else "nenhum (já estava igual à vitrine)"))
    if not a.sem_pendencias:
        pend = pendencias(grupos, dados)
        print(f"\npendências ({len(pend)}) — nada disso foi alterado:")
        for x in pend:
            print("  - " + x)


if __name__ == "__main__":
    main()
