
import os, struct
from pathlib import Path
from PIL import Image
from kivy.app import App
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image as KImage
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, RoundedRectangle

TEXTURE_CHUNK=0x7A0B60DA
NAMES_CHUNK=0x4C9B9EB2
FORMATS={0:"DXT1",1:"DXT3",2:"DXT5",3:"RGBA8"}

def u16(b,o): return struct.unpack_from("<H",b,o)[0]
def u32(b,o): return struct.unpack_from("<I",b,o)[0]

def rgb565(v):
    return ((v>>11&31)*255//31,(v>>5&63)*255//63,(v&31)*255//31)

def decode_dxt(raw,w,h,kind):
    out=bytearray(w*h*4); bw=(w+3)//4; bh=(h+3)//4; p=0
    for by in range(bh):
        for bx in range(bw):
            if kind==0:
                c0,c1=struct.unpack_from("<HH",raw,p); bits=u32(raw,p+4); p+=8
                a,b=rgb565(c0),rgb565(c1)
                cs=[(*a,255),(*b,255)]
                cs += [((2*a[0]+b[0])//3,(2*a[1]+b[1])//3,(2*a[2]+b[2])//3,255),
                       ((a[0]+2*b[0])//3,(a[1]+2*b[1])//3,(a[2]+2*b[2])//3,255)] if c0>c1 else [((a[0]+b[0])//2,(a[1]+b[1])//2,(a[2]+b[2])//2,255),(0,0,0,0)]
                for j in range(4):
                    for i in range(4):
                        x,y=bx*4+i,by*4+j
                        if x<w and y<h: out[(y*w+x)*4:(y*w+x)*4+4]=bytes(cs[(bits>>(2*(4*j+i)))&3])
            elif kind==1:
                ab=raw[p:p+8]; c0,c1=struct.unpack_from("<HH",raw,p+8); bits=u32(raw,p+12); p+=16
                av=int.from_bytes(ab,"little"); a,b=rgb565(c0),rgb565(c1)
                cs=[(*a,255),(*b,255),((2*a[0]+b[0])//3,(2*a[1]+b[1])//3,(2*a[2]+b[2])//3,255),((a[0]+2*b[0])//3,(a[1]+2*b[1])//3,(a[2]+2*b[2])//3,255)]
                for j in range(4):
                    for i in range(4):
                        x,y=bx*4+i,by*4+j
                        if x<w and y<h:
                            c=cs[(bits>>(2*(4*j+i)))&3]; al=((av>>(4*(4*j+i)))&15)*17
                            out[(y*w+x)*4:(y*w+x)*4+4]=bytes((c[0],c[1],c[2],al))
            else:
                a0,a1=raw[p],raw[p+1]; ab=int.from_bytes(raw[p+2:p+8],"little")
                c0,c1=struct.unpack_from("<HH",raw,p+8); bits=u32(raw,p+12); p+=16
                aa=[a0,a1,(6*a0+a1)//7,(5*a0+2*a1)//7,(4*a0+3*a1)//7,(3*a0+4*a1)//7,(2*a0+5*a1)//7,(a0+6*a1)//7] if a0>a1 else [a0,a1,(4*a0+a1)//5,(3*a0+2*a1)//5,(2*a0+3*a1)//5,(a0+4*a1)//5,0,255]
                a,b=rgb565(c0),rgb565(c1)
                cs=[a,b,((2*a[0]+b[0])//3,(2*a[1]+b[1])//3,(2*a[2]+b[2])//3),((a[0]+2*b[0])//3,(a[1]+2*b[1])//3,(a[2]+2*b[2])//3)]
                for j in range(4):
                    for i in range(4):
                        x,y=bx*4+i,by*4+j
                        if x<w and y<h:
                            c=cs[(bits>>(2*(4*j+i)))&3]; al=aa[(ab>>(3*(4*j+i)))&7]
                            out[(y*w+x)*4:(y*w+x)*4+4]=bytes((*c,al))
    return bytes(out)

def decode(raw,w,h,fmt):
    if fmt==3:return raw[:w*h*4]
    if fmt in (0,1,2):return decode_dxt(raw,w,h,fmt)
    raise ValueError("Unsupported texture format: "+str(fmt))

def parse_rx3(data):
    if data[:4]!=b"RX3l":
        raise ValueError("Bukan RX3l. ChunLZMA wrapper belum didukung di v0.1.")
    count=u32(data,12); chunks=[]; p=16
    for _ in range(count):
        typ,off,size,pad=struct.unpack_from("<IIII",data,p); chunks.append((typ,off,size)); p+=16
    names=[]
    for typ,off,size in chunks:
        if typ==NAMES_CHUNK and size>=16:
            n=u32(data,off+4); q=off+16
            for _ in range(n):
                if q+8>off+size:break
                t,s=struct.unpack_from("<II",data,q); q+=8
                if q+s>off+size:break
                names.append((t,data[q:q+s].split(b"\0",1)[0].decode("utf8","replace"))); q+=s
    tex=[c for c in chunks if c[0]==TEXTURE_CHUNK]
    texnames=[n for t,n in names if t==TEXTURE_CHUNK]
    result=[]
    for i,(typ,off,size) in enumerate(tex):
        w,h=u16(data,off+8),u16(data,off+10); depth=u16(data,off+12); mips=u16(data,off+14); fmt=data[off+5]
        levels=[]; q=off+16
        for face in range(depth):
            for mip in range(mips):
                stride,lines,sz,pad=struct.unpack_from("<IIII",data,q); levels.append((face,mip,q+16,sz)); q+=16+sz
        result.append({"name":texnames[i] if i<len(texnames) else f"texture_{i}","w":w,"h":h,"fmt":fmt,"levels":levels})
    if not result: raise ValueError("Tidak menemukan texture chunk.")
    return result

def popup_file(title,callback,filters):
    box=BoxLayout(orientation="vertical")
    fc=FileChooserListView(path="/storage/emulated/0",filters=filters); box.add_widget(fc)
    row=BoxLayout(size_hint_y=None,height=dp(48)); cancel=Button(text="BATAL"); ok=Button(text="PILIH")
    row.add_widget(cancel); row.add_widget(ok); box.add_widget(row)
    pop=Popup(title=title,content=box,size_hint=(.95,.9)); cancel.bind(on_release=pop.dismiss)
    def choose(_):
        if fc.selection: pop.dismiss(); callback(fc.selection[0])
    ok.bind(on_release=choose); pop.open()

class Base(Screen):
    def msg(self,t,m): Popup(title=t,content=Label(text=str(m)),size_hint=(.88,.35)).open()

class OpenScreen(Base):
    def __init__(self,**kw):
        super().__init__(**kw); box=BoxLayout()
        with box.canvas.before:
            Color(0.02,0.58,0.93,1); self.bg=RoundedRectangle(pos=box.pos,size=box.size)
        box.bind(pos=self.sync,size=self.sync)
        b=Button(text="OPEN",font_size=dp(28),color=(1,1,1,1),background_normal="")
        b.bind(on_release=lambda *_: setattr(self.manager,"current","files")); box.add_widget(b); self.add_widget(box)
    def sync(self,*_): self.bg.pos=self.pos; self.bg.size=self.size

class FilesScreen(Base):
    def __init__(self,**kw):
        super().__init__(**kw); self.items=[]; self.delete_mode=False
        root=BoxLayout(orientation="vertical")
        head=BoxLayout(size_hint_y=None,height=dp(70))
        back=Button(text="< back",font_size=dp(25),color=(0.02,0.62,0.88,1),background_normal="")
        choose=Button(text="pilih >",font_size=dp(25),color=(0.02,0.62,0.88,1),background_normal="")
        head.add_widget(back); head.add_widget(Label()); head.add_widget(choose)
        back.bind(on_release=lambda *_: setattr(self.manager,"current","open")); choose.bind(on_release=self.go)
        root.add_widget(head)
        self.listbox=BoxLayout(orientation="vertical",spacing=dp(10),padding=dp(16),size_hint_y=None); self.listbox.bind(minimum_height=self.listbox.setter("height"))
        sc=ScrollView(); sc.add_widget(self.listbox); root.add_widget(sc)
        plus=Button(text="+",font_size=dp(52),color=(0.02,0.62,0.88,1),background_normal="",size_hint_y=None,height=dp(110))
        plus.bind(on_release=lambda *_: popup_file("Tambah RX3",self.add,["*.rx3","*"])); root.add_widget(plus)
        self.add_widget(root)
    def on_pre_enter(self,*_): self.refresh()
    def refresh(self):
        self.listbox.clear_widgets()
        for i,p in enumerate(self.items):
            b=Button(text=Path(p).name,font_size=dp(18),size_hint_y=None,height=dp(65),background_normal="")
            b.bind(on_release=lambda _,j=i:self.remove(j) if self.delete_mode else None); self.listbox.add_widget(b)
    def add(self,p):
        if p not in self.items:self.items.append(p); self.refresh()
    def remove(self,i):
        self.items.pop(i); self.delete_mode=False; self.refresh()
    def go(self,*_):
        if not self.items:self.msg("RX3","Tambahkan RX3 terlebih dahulu."); return
        self.manager.get_screen("edit").load(self.items[0]); self.manager.current="edit"

class EditScreen(Base):
    def __init__(self,**kw):
        super().__init__(**kw); self.data=None; self.path=None; self.tex=[]; self.selected=None
        root=BoxLayout(orientation="vertical")
        head=BoxLayout(size_hint_y=None,height=dp(68))
        back=Button(text="< back",font_size=dp(24),color=(0.02,0.62,0.88,1),background_normal="")
        imp=Button(text="import",font_size=dp(24),color=(0.02,0.62,0.88,1),background_normal="")
        exp=Button(text="export",font_size=dp(24),color=(0.02,0.62,0.88,1),background_normal="")
        head.add_widget(back); head.add_widget(Label()); head.add_widget(imp); head.add_widget(exp)
        back.bind(on_release=lambda *_: setattr(self.manager,"current","files")); imp.bind(on_release=self.import_tex); exp.bind(on_release=self.export)
        root.add_widget(head)
        panel=BoxLayout(padding=dp(14))
        with panel.canvas.before:
            Color(.92,.92,.92,1); self.pr=RoundedRectangle(pos=panel.pos,size=panel.size,radius=[dp(18)])
        panel.bind(pos=lambda *_:self.bg(panel),size=lambda *_:self.bg(panel))
        self.preview=KImage(allow_stretch=True,keep_ratio=True); panel.add_widget(self.preview); root.add_widget(panel)
        self.status=Label(text="",size_hint_y=None,height=dp(35)); root.add_widget(self.status)
        sc=ScrollView(do_scroll_y=False,size_hint_y=None,height=dp(150))
        self.row=BoxLayout(orientation="horizontal",spacing=dp(10),padding=dp(8),size_hint_x=None); self.row.bind(minimum_width=self.row.setter("width")); sc.add_widget(self.row); root.add_widget(sc)
        save=Button(text="SIMPAN RX3",size_hint_y=None,height=dp(58),font_size=dp(18)); save.bind(on_release=self.save); root.add_widget(save)
        self.add_widget(root)
    def bg(self,p): self.pr.pos=p.pos; self.pr.size=p.size
    def load(self,p):
        try:
            self.path=Path(p); self.data=bytearray(self.path.read_bytes()); self.tex=parse_rx3(self.data); self.selected=None; self.row.clear_widgets()
            for i,t in enumerate(self.tex):
                b=Button(text=t["name"],font_size=dp(12),size_hint=(None,1),width=dp(130),background_normal="")
                b.bind(on_release=lambda _,j=i:self.select(j)); self.row.add_widget(b)
            self.status.text=f"{self.path.name} • {len(self.tex)} texture"
            self.select(0)
        except Exception as e:self.msg("RX3 ERROR",e)
    def select(self,i):
        try:
            self.selected=i; t=self.tex[i]; lev=next(x for x in t["levels"] if x[0]==0 and x[1]==0)
            rgba=decode(self.data[lev[2]:lev[2]+lev[3]],t["w"],t["h"],t["fmt"])
            out=Path(App.get_running_app().user_data_dir)/"_preview.png"; Image.frombytes("RGBA",(t["w"],t["h"]),rgba).save(out)
            self.preview.source=str(out); self.preview.reload(); self.status.text=f'{t["name"]} • {t["w"]}×{t["h"]} • {FORMATS.get(t["fmt"],"unknown")}'
        except Exception as e:self.msg("PREVIEW ERROR",e)
    def export(self,*_):
        if not self.tex:return
        try:
            out=Path("/storage/emulated/0/Download")/(self.path.stem+"_textures"); out.mkdir(parents=True,exist_ok=True)
            ids=[self.selected] if self.selected is not None else range(len(self.tex))
            for i in ids:
                t=self.tex[i]; lev=next(x for x in t["levels"] if x[0]==0 and x[1]==0); rgba=decode(self.data[lev[2]:lev[2]+lev[3]],t["w"],t["h"],t["fmt"])
                safe="".join(c if c.isalnum() or c in "_-" else "_" for c in t["name"])
                Image.frombytes("RGBA",(t["w"],t["h"]),rgba).save(out/(safe+".png"))
            self.msg("EXPORT",f"Disimpan di {out}")
        except Exception as e:self.msg("EXPORT ERROR",e)
    def import_tex(self,*_):
        if self.selected is None:self.msg("IMPORT","Pilih texture terlebih dahulu."); return
        popup_file("Import PNG",self.replace,["*.png","*"])
    def replace(self,p):
        try:
            t=self.tex[self.selected]
            if t["fmt"]!=3:raise ValueError("Import v1 baru mendukung RGBA8. Format: "+FORMATS.get(t["fmt"],"unknown"))
            img=Image.open(p).convert("RGBA")
            if img.size!=(t["w"],t["h"]):raise ValueError(f"Ukuran harus {t['w']}×{t['h']}.")
            for face,mip,off,sz in t["levels"]:
                w=max(1,t["w"]>>mip); h=max(1,t["h"]>>mip); raw=img.resize((w,h),Image.Resampling.LANCZOS).tobytes("raw","RGBA")
                if len(raw)!=sz:raise ValueError("Ukuran mip tidak cocok.")
                self.data[off:off+sz]=raw
            self.select(self.selected); self.msg("IMPORT","Berhasil. Tekan SIMPAN RX3.")
        except Exception as e:self.msg("IMPORT ERROR",e)
    def save(self,*_):
        if self.data is None:return
        out=Path("/storage/emulated/0/Download")/(self.path.stem+"_edited.rx3"); out.write_bytes(self.data); self.msg("SIMPAN",out)

class RX3App(App):
    def build(self):
        sm=ScreenManager(); sm.add_widget(OpenScreen(name="open")); sm.add_widget(FilesScreen(name="files")); sm.add_widget(EditScreen(name="edit")); return sm

if __name__=="__main__": RX3App().run()
