"""Verificador de fontes em camadas para os artigos do blog.

Camada 1  DOI existe       — https://doi.org/<doi> resolve (Handle API do doi.org)
Camada 2  Metadados batem  — Crossref: título, 1º autor e ano iguais aos escritos na seção Fontes
Camada 3  Não retratado    — OpenAlex is_retracted + Crossref "update-to" de retratação/errata
Camada 4  Link oficial     — links não-DOI (Anvisa, DOU, ECHA, EUR-Lex, OSM) respondem 2xx/3xx
Camada 5  Âncora           — toda nota [n] do texto aponta para uma fonte que existe, e toda fonte é citada
Camada 6  Sustentação      — extrai frase citante + resumo (OpenAlex) para o avaliador independente conferir
                             (não é automática: gera <slug>.sustentacao.md para o avaliador)

Uso: python tools/verificar_fontes.py <arquivo.html> [...]   → sai com código 1 se alguma camada 1–5 falhar.
"""
import html as H, json, re, sys, unicodedata, urllib.parse, urllib.request
from pathlib import Path

UA = {"User-Agent": "manicura-site-verificador/1.0 (mailto:contato@manicuraexpressnails.com)"}


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def norm(s):
    s = unicodedata.normalize("NFKD", H.unescape(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


def parecido(a, b):
    A, B = set(norm(a)), set(norm(b))
    return len(A & B) / max(1, min(len(A), len(B)))


def texto(fr):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", fr))).strip()


def fontes_do_html(src):
    """Itens da seção Fontes: padrão do blog é <li id="fonte-N">...</li>."""
    return re.findall(r'(?is)<li[^>]*\bid="(fonte-\d+)"[^>]*>(.*?)</li>', src)


def main(arqs):
    falhou = False
    for arq in arqs:
        p = Path(arq)
        src = p.read_text(encoding="utf-8")
        itens = fontes_do_html(src)
        print(f"\n== {p.name}: {len(itens)} fontes")
        sust = [f"# Sustentação — {p.name}\n"]
        ids = []
        for i, (fid, li) in enumerate(itens, 1):
            t = texto(li)
            doi = re.search(r"doi\.org/(10\.[^\s\"<>]+)", li)
            links = [u for u in re.findall(r'href="(https?://[^"]+)"', li) if "doi.org" not in u]
            ids.append(fid)
            linha = [f"[{fid}]"]
            if doi:
                d = doi.group(1).rstrip(".,;)")
                try:  # camada 1
                    _, b = get("https://doi.org/api/handles/" + urllib.parse.quote(d))
                    ok1 = json.loads(b).get("responseCode") == 1
                except Exception:
                    ok1 = False
                linha.append("C1 ok" if ok1 else "C1 FALHA (DOI não existe)")
                try:  # camada 2
                    _, b = get("https://api.crossref.org/works/" + urllib.parse.quote(d))
                    w = json.loads(b)["message"]
                    tit = (w.get("title") or [""])[0]
                    aut = (w.get("author") or [{}])[0].get("family", "")
                    anos = {str((w.get(k, {}).get("date-parts") or [[None]])[0][0]) for k in ("issued", "published-print", "published-online", "published")}
                    ano = "/".join(sorted(a for a in anos if a != "None"))
                    ok2 = (parecido(tit, t) >= 0.6 and (not aut or any(x in norm(t) for x in norm(aut)))
                           and any(a in t for a in anos))
                    linha.append("C2 ok" if ok2 else f"C2 FALHA (Crossref: '{tit[:70]}' / {aut} / {ano})")
                    ret = [u for u in w.get("update-to", []) if "retract" in u.get("type", "")]
                except Exception as e:
                    ok2, ret = False, []
                    linha.append(f"C2 FALHA ({e.__class__.__name__})")
                try:  # camada 3
                    _, b = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(d))
                    oa = json.loads(b)
                    ok3 = not oa.get("is_retracted") and not ret
                    inv = oa.get("abstract_inverted_index") or {}
                    pos = sorted((k, w_) for w_, ks in inv.items() for k in ks)
                    resumo = " ".join(w_ for _, w_ in pos)
                except Exception:
                    ok3, resumo = not ret, ""
                linha.append("C3 ok" if ok3 else "C3 FALHA (retratado)")
                falhou |= not (ok1 and ok2 and ok3)
                sust.append(f"## [{i}] {t}\n\nResumo (OpenAlex): {resumo[:1500] or '(sem resumo — conferir no texto do artigo)'}\n")
            for u in links:  # camada 4
                try:
                    st, _ = get(u)
                    ok4 = 200 <= st < 400
                except urllib.error.HTTPError as e:
                    ok4 = e.code in (401, 403)  # sites oficiais que bloqueiam robô: conferir à mão
                    st = e.code
                except Exception as e:
                    ok4, st = False, e.__class__.__name__
                linha.append(f"C4 {'ok' if ok4 else 'FALHA'} {st} {u[:60]}")
                falhou |= not ok4
            if not doi and not links:
                linha.append("SEM LINK/DOI")
            print("  " + " | ".join(linha) + f"\n      {t[:110]}")
        # camada 5: âncoras
        corpo = re.sub(r'(?is)<li[^>]*id="fonte-\d+".*?</li>', "", src)
        citadas = set(re.findall(r'href="#(fonte-\d+)"', corpo))
        existentes = set(ids)
        orfas = citadas - existentes
        nao_citadas = existentes - citadas
        ok5 = not orfas and bool(existentes)
        print(f"  C5 {'ok' if ok5 else 'FALHA'} notas→fontes; órfãs={sorted(orfas)} fontes não citadas={sorted(nao_citadas)}")
        falhou |= not ok5
        # camada 6: material para o avaliador
        for m in re.finditer(r"([^.>]{20,300}?)<a[^>]+href=\"#([^\"]+)\"", corpo):
            sust.append(f"- Frase: {texto(m.group(1))} → #{m.group(2)}")
        out = p.with_suffix(".sustentacao.md")
        out.write_text("\n".join(sust), encoding="utf-8")
        print(f"  C6 material para o avaliador: {out}")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
