"""Gera as miniaturas de compartilhamento (og:image, 1200x630) de cada página em img/og/.
Uso: python tools/gerar_og.py   (depois, as páginas já apontam para img/og/<pagina>.jpg)"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

R = Path(__file__).resolve().parent.parent
FONTES = Path(r"C:/Users/Usuario/Downloads/Projects/gift-moment-semijoias/fonts")
TERRA, TERRA_E, NUDE = (180, 99, 66), (142, 74, 44), (251, 245, 238)
LOGO = R / "img" / "site" / "kzq2zhs-og.png"  # logo terracota do topo do site
NAYARA = R / "img" / "nayara-das-dores-santos-manicura-express-768.webp"

PAGINAS = {
    "index": ("img/site/OE4gyFL.webp", "Manicure e esmaltação em gel em 30 minutos"),
    "servicos-jundiai": ("img/site/qMzx7Ca.webp", "Esmaltação em gel e alongamento de unhas"),
    "sobre-nayara-jundiai": (NAYARA, "Nayara das Dores Santos, quem cuida das suas unhas"),
    "contato-jundiai": (NAYARA, "Agende o SEU MOMENTO no Anhangabaú"),
    "manicure-anhangabau-jundiai": ("img/site/sMd54TO.webp", "Manicure no Anhangabaú, em Jundiaí"),
    "gift-moment-jundiai": ("img/site/b9MxCim.webp", "Gift Moment: presentes e vale-presente"),
    "semijoias-jundiai": ("img/site/sLR31YM.webp", "Semijoias Gift Moment: pronta entrega em até 3x"),
    "blog-jundiai": ("img/site/Cpp0TFl.webp", "Química, segurança e cuidado com as unhas"),
    "artigo-autoclave-vs-estufa-jundiai": ("img/site/rEJjyPw.webp", "Autoclave ou estufa: qual realmente esteriliza?"),
    "artigo-cabine-alergia-jundiai": ("img/site/cabine-onail-acesa-bancada-jundiai.webp", "Cabine fraca causa alergia ao gel?"),
    "protocolo-biosseguranca-jundiai": ("img/site/HBktedt.webp", "Biossegurança: autoclave a 134 °C"),
    "reflexologia-shiatsu-jundiai": ("img/site/CLEy6Dd.webp", "Reflexologia e shiatsu: o SEU MOMENTO"),
    "esmaltacao-em-gel-jundiai": ("img/site/esmaltacao-gel-nude-cabine-onail-jundiai.webp", "Esmaltação em gel em Jundiaí"),
    "alongamento-de-unhas-jundiai": ("img/site/unhas-amendoadas-francesinha-base-rosada-jundiai.webp", "Alongamento de unhas em Jundiaí"),
    "pedicure-jundiai": ("img/site/estudio-manicura-express-nails-panoramica-jundiai.webp", "Pedicure em Jundiaí, no Anhangabaú"),
}
FOCO = {"sobre-nayara-jundiai": (0.5, 0.35), "contato-jundiai": (0.5, 0.12), "pedicure-jundiai": (0.35, 0.5)}


def fonte(nome, tam, peso):
    f = ImageFont.truetype(str(FONTES / nome), tam)
    try: f.set_variation_by_axes([peso])
    except Exception: pass
    return f


def quebrar(d, texto, f, larg):
    linhas, atual = [], ""
    for p in texto.split():
        t = (atual + " " + p).strip()
        if d.textlength(t, font=f) <= larg: atual = t
        else: linhas.append(atual); atual = p
    return linhas + [atual]


def cartao(foto, titulo, foco=(0.5, 0.5)):
    img = Image.new("RGB", (1200, 630), NUDE)
    ft = ImageOps.fit(Image.open(foto).convert("RGB"), (600, 630), Image.LANCZOS, centering=foco)
    img.paste(ft, (0, 0))
    d = ImageDraw.Draw(img)
    logo = Image.open(LOGO).convert("RGBA"); logo = logo.crop(logo.getbbox()); logo.thumbnail((400, 130), Image.LANCZOS)
    img.paste(logo, (600 + (600 - logo.width) // 2, 50), logo)
    for tam in (54, 48, 42):
        f = fonte("Raleway[wght].ttf", tam, 700); ls = quebrar(d, titulo, f, 500)
        if len(ls) <= 4: break
    alt = len(ls) * (tam + 14); y = 230 + (260 - alt) // 2
    for l in ls:
        d.text((900 - d.textlength(l, font=f) / 2, y), l, font=f, fill=TERRA_E); y += tam + 14
    fr = fonte("Montserrat[wght].ttf", 24, 500)
    r = "manicuraexpressnails.com · Jundiaí/SP"
    d.text((900 - d.textlength(r, font=fr) / 2, 560), r, font=fr, fill=TERRA)
    d.rectangle((600, 0, 606, 630), fill=TERRA)
    return img


def cabine():
    base = ImageOps.fit(Image.open(R / "img/site/onail-ia-legendado-pt-poster.webp").convert("RGB"), (1200, 630), Image.LANCZOS, centering=(0.5, 0.6))
    d = ImageDraw.Draw(base, "RGBA")
    f = fonte("Montserrat[wght].ttf", 34, 650)
    t = "A primeira cabine de unhas com IA de Jundiaí"
    w = d.textlength(t, font=f)
    d.rounded_rectangle((36, 34, 36 + w + 56, 34 + 70), radius=35, fill=(180, 99, 66, 235))
    d.text((64, 50), t, font=f, fill=(255, 255, 255))
    return base


def main():
    out = R / "img" / "og"; out.mkdir(exist_ok=True)
    for pag, (foto, titulo) in PAGINAS.items():
        cartao(R / foto if isinstance(foto, str) else foto, titulo, FOCO.get(pag, (0.5, 0.5))).save(out / f"{pag}.jpg", quality=86, optimize=True)
    cabine().save(out / "cabine-onail-jundiai.jpg", quality=86, optimize=True)
    print("ok:", len(PAGINAS) + 1, "miniaturas em img/og/")


if __name__ == "__main__":
    main()
