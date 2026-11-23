from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,io,base64,html,hashlib
from PIL import Image,ImageOps
from maps import ROOT,OUT

def main():
    results=json.loads((OUT/'Проверка.json').read_text(encoding='utf8'));assert results['проверка']['файлы_STL']==928
    archive=ROOT/'Море имён — полный комплект.zip';files=sorted(p for p in OUT.rglob('*') if p.is_file())
    with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.relative_to(OUT))
    with ZipFile(archive) as z:
        assert len(z.namelist())==len(files) and z.testzip() is None
        for f in files:assert hashlib.sha256(f.read_bytes()).digest()==hashlib.sha256(z.read(f.relative_to(OUT).as_posix())).digest()
    print('ZIP:',len(files),'files;',round(archive.stat().st_size/(1024**2),1),'MiB')
    prep=ROOT/'qa-temp';prep.mkdir(exist_ok=True)
    sources=[('Карта берегов',OUT/'Карта мира.png'),('Карточки и знаки',OUT/'Галерея/Карточки и знаки.png'),('Герои',OUT/'Галерея/Герои на базах.png'),('Чудовища',OUT/'Галерея/Бестиарий на базах.png'),('Планшет и декор',OUT/'Галерея/Мастерская.png'),('Столицы и деревни',OUT/'Галерея/Поселения 1.png')];labels=[];pics=[]
    for i,(title,f) in enumerate(sources):
        im=ImageOps.contain(Image.open(f).convert('RGB'),(1010,690));buf=io.BytesIO();im.save(buf,format='JPEG',quality=76,optimize=True);data=base64.b64encode(buf.getvalue()).decode();labels.append(f'<button type="button" aria-pressed="{str(i==0).lower()}" onclick="choose({i})">{html.escape(title)}</button>');pics.append(f'<figure style="display:{"block" if i==0 else "none"}"><img src="data:image/jpeg;base64,{data}" alt="{html.escape(title)}"></figure>')
    css='*{box-sizing:border-box}nav{display:flex;gap:5px;flex-wrap:wrap;margin:2px 0 10px}button{background:var(--secondary);color:var(--foreground);border:1px solid var(--border);border-radius:var(--radius);padding:5px 9px;font:inherit;font-size:12px;cursor:pointer}button[aria-pressed=true]{background:var(--primary);color:var(--primary-foreground)}button:focus-visible{outline:2px solid var(--ring)}figure{margin:0}img{display:block;width:100%;border-radius:var(--radius)}'
    script="function choose(i){document.querySelectorAll('figure').forEach((el,j)=>el.style.display=i===j?'block':'none');document.querySelectorAll('button').forEach((el,j)=>el.setAttribute('aria-pressed',String(i===j)));}"
    (prep/'gallery.html').write_text('<!doctype html><html lang=ru><meta charset=utf-8><style>'+css+'</style><nav aria-label="Материалы игры">'+''.join(labels)+'</nav>'+''.join(pics)+'<script>'+script+'</script></html>',encoding='utf8')
if __name__=='__main__':main()
