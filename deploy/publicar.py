"""Publica o site na Hostinger a partir do git (roda na VPS, onde ficam as credenciais FTP).

Fluxo: PC (edita + commit) → GitHub → VPS (/opt/manicura-site: git pull) → Hostinger (este script).

  python3 deploy/publicar.py --rascunho            sobe os alterados desde o último deploy em _rascunhos/site/ (site vivo intocado)
  python3 deploy/publicar.py --producao            sobe os alterados desde o último deploy pra raiz do site
  python3 deploy/publicar.py --producao --tudo     sobe TODOS os arquivos versionados (use só se o controle se perder)
  (acrescente --simular para só listar)

Antes de sobrescrever na produção, baixa a versão que está no ar para /root/backups/site/<data>/.
O último commit publicado fica em .ultimo-deploy (fora do git).
"""
import ftplib, io, os, subprocess, sys, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENV = Path("/app/manicura_express/.env")
MARCA = RAIZ / ".ultimo-deploy"
IGNORAR = {".gitattributes", ".gitignore", "README.md"}


def env():
    d = {}
    for l in ENV.read_text().splitlines():
        if "=" in l and not l.lstrip().startswith("#"):
            k, v = l.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def git(*a):
    return subprocess.check_output(["git", "-C", str(RAIZ), *a], text=True).strip()


def arquivos(tudo):
    if tudo or not MARCA.exists():
        lista = git("ls-files").splitlines()
        apagados = []
    else:
        base = MARCA.read_text().strip()
        lista = git("diff", "--name-only", "--diff-filter=ACMR", base, "HEAD").splitlines()
        apagados = git("diff", "--name-only", "--diff-filter=D", base, "HEAD").splitlines()
    ok = lambda p: p and p not in IGNORAR and not p.startswith("deploy/")  # noqa: E731
    return [p for p in lista if ok(p)], [p for p in apagados if ok(p)]


def garantir_pasta(ftp, pasta):
    atual = ""
    for parte in [p for p in pasta.split("/") if p]:
        atual = f"{atual}/{parte}" if atual else parte
        try:
            ftp.mkd(atual)
        except ftplib.error_perm:
            pass  # já existe


def main():
    rascunho, producao = "--rascunho" in sys.argv, "--producao" in sys.argv
    simular, tudo = "--simular" in sys.argv, "--tudo" in sys.argv
    if rascunho == producao:
        sys.exit("use --rascunho OU --producao")
    if git("status", "--porcelain", "--untracked-files=no"):
        sys.exit("há mudanças não commitadas na VPS — publique só o que está no git")

    enviar, apagar = arquivos(tudo)
    destino = "_rascunhos/site/" if rascunho else ""
    head = git("rev-parse", "--short", "HEAD")
    print(f"{'RASCUNHO' if rascunho else 'PRODUÇÃO'} @ {head}: {len(enviar)} p/ enviar, {len(apagar)} p/ apagar")
    for p in enviar:
        print("  +", p)
    for p in apagar:
        print("  -", p)
    if simular or not (enviar or apagar):
        return

    e = env()
    ftp = ftplib.FTP()
    ftp.connect(e["HOSTINGER_FTP_HOST"], int(e.get("HOSTINGER_FTP_PORT", 21)), timeout=60)
    ftp.login(e["HOSTINGER_FTP_USER"], e["HOSTINGER_FTP_PASSWORD"])

    if producao:  # backup do que vai ser sobrescrito/apagado
        bk = Path(f"/root/backups/site/{time.strftime('%Y%m%d_%H%M%S')}_{head}")
        for p in enviar + apagar:
            buf = io.BytesIO()
            try:
                ftp.retrbinary(f"RETR {p}", buf.write)
            except ftplib.error_perm:
                continue  # arquivo novo
            (bk / p).parent.mkdir(parents=True, exist_ok=True)
            (bk / p).write_bytes(buf.getvalue())
        print("backup:", bk)

    for p in enviar:
        remoto = destino + p
        garantir_pasta(ftp, os.path.dirname(remoto))
        with open(RAIZ / p, "rb") as f:
            ftp.storbinary(f"STOR {remoto}", f)
    for p in (apagar if producao else []):  # rascunho nunca apaga nada do site vivo
        try:
            ftp.delete(p)
        except ftplib.error_perm:
            pass
    ftp.quit()

    if producao:
        MARCA.write_text(git("rev-parse", "HEAD"))
    url = e.get("HOSTINGER_SITE_URL", "https://manicuraexpressnails.com").rstrip("/")
    print("ok →", f"{url}/{destino}")


if __name__ == "__main__":
    main()
