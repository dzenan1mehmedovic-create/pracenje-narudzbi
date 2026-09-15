import streamlit as st
import pandas as pd
import requests
from datetime import date
from io import BytesIO

st.set_page_config(page_title='Order Hub', page_icon='📦', layout='wide', initial_sidebar_state='expanded')

# ---------- FUTURISTIC UI ----------
st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{font-family:Inter,sans-serif}.stApp{background:radial-gradient(circle at 8% 0%,rgba(0,229,255,.11),transparent 28%),radial-gradient(circle at 95% 8%,rgba(124,58,237,.14),transparent 30%),#060a12}.block-container{max-width:1450px;padding-top:1.5rem;padding-bottom:3rem}.hero{padding:30px;border-radius:24px;border:1px solid rgba(0,229,255,.18);background:linear-gradient(135deg,rgba(12,24,40,.94),rgba(17,13,35,.94));box-shadow:0 0 45px rgba(0,229,255,.07);margin-bottom:22px}.eyebrow{font-size:.75rem;letter-spacing:.16em;font-weight:800;color:#63eaff}.hero h1{font-size:2.35rem;margin:.25rem 0}.muted{color:#93a2b8}.card{padding:18px;border-radius:18px;border:1px solid rgba(255,255,255,.07);background:rgba(13,20,33,.82)}[data-testid='stMetric']{background:linear-gradient(145deg,rgba(15,27,45,.95),rgba(10,15,26,.95));border:1px solid rgba(0,229,255,.12);border-radius:18px;padding:15px}.stButton>button,.stDownloadButton>button{border-radius:12px;border:1px solid rgba(0,229,255,.22);font-weight:700;background:linear-gradient(135deg,#10263a,#19162d);color:white}.stButton>button:hover,.stDownloadButton>button:hover{border-color:#00e5ff;box-shadow:0 0 18px rgba(0,229,255,.15)}div[data-testid='stExpander']{border:1px solid rgba(255,255,255,.08);border-radius:16px;background:rgba(8,14,25,.65)}.badge{display:inline-block;padding:5px 10px;border-radius:99px;background:rgba(0,229,255,.08);border:1px solid rgba(0,229,255,.18);color:#8defff;font-size:.72rem;font-weight:800}.section{font-size:.78rem;letter-spacing:.12em;font-weight:800;color:#63eaff;text-transform:uppercase;margin:12px 0 7px}.small{font-size:.84rem;color:#93a2b8}
</style>
''', unsafe_allow_html=True)

SUPABASE_URL = st.secrets['SUPABASE_URL'].rstrip('/')
SUPABASE_KEY = st.secrets.get('SUPABASE_PUBLISHABLE_KEY', st.secrets.get('SUPABASE_SECRET_KEY',''))
TABLE='narudzbe'; BUCKET='fakture'
STATUS=['Čeka odgovor','Naručeno','U dolasku','Stiglo','Problem','Otkazano']; ODG=['Da','Ne','Djelimično']

def headers(token=None): return {'apikey':SUPABASE_KEY,'Authorization':f"Bearer {token or SUPABASE_KEY}",'Content-Type':'application/json','Prefer':'return=representation'}
def url(): return f'{SUPABASE_URL}/rest/v1/{TABLE}'

def auth_login(email,password):
    r=requests.post(f'{SUPABASE_URL}/auth/v1/token?grant_type=password',headers={'apikey':SUPABASE_KEY,'Content-Type':'application/json'},json={'email':email,'password':password},timeout=20)
    if r.status_code==200:
        d=r.json(); st.session_state.update(logged_in=True,access_token=d['access_token'],user_id=d['user']['id'],email=d['user'].get('email',email)); return True,''
    return False,r.json().get('msg',r.text)

def auth_register(email,password):
    r=requests.post(f'{SUPABASE_URL}/auth/v1/signup',headers={'apikey':SUPABASE_KEY,'Content-Type':'application/json'},json={'email':email,'password':password},timeout=20)
    if r.status_code in (200,201):
        d=r.json()
        if d.get('access_token'):
            st.session_state.update(logged_in=True,access_token=d['access_token'],user_id=d['user']['id'],email=d['user'].get('email',email))
        return True, 'Registracija uspješna. Ako je uključena potvrda emaila, potvrdi email pa se prijavi.'
    return False,r.json().get('msg',r.text)

def login_screen():
    st.markdown("<div class='hero'><div class='eyebrow'>ORDER CONTROL SYSTEM • ONLINE</div><h1>📦 Order Hub</h1><div class='muted'>Centralno mjesto za narudžbe, rokove, statuse i fakture.</div></div>",unsafe_allow_html=True)
    a,b=st.tabs(['🔐 Prijava','➕ Registracija'])
    with a:
        with st.form('login'):
            e=st.text_input('Email'); p=st.text_input('Lozinka',type='password')
            if st.form_submit_button('UĐI U SISTEM',use_container_width=True):
                ok,msg=auth_login(e.strip(),p); st.error(msg) if not ok else st.rerun()
    with b:
        with st.form('register'):
            e=st.text_input('Email',key='re'); p=st.text_input('Lozinka',type='password',key='rp'); p2=st.text_input('Ponovi lozinku',type='password')
            if st.form_submit_button('KREIRAJ RAČUN',use_container_width=True):
                if p!=p2: st.error('Lozinke se ne podudaraju.')
                elif len(p)<6: st.error('Lozinka mora imati najmanje 6 znakova.')
                else:
                    ok,msg=auth_register(e.strip(),p); (st.rerun() if ok and st.session_state.get('logged_in') else st.success(msg)) if ok else st.error(msg)

if not st.session_state.get('logged_in'):
    login_screen(); st.stop()
TOKEN=st.session_state.access_token

def load():
    r=requests.get(url(),headers=headers(TOKEN),params={'select':'*','order':'id.desc'},timeout=20)
    if r.status_code!=200: st.error('Greška pri učitavanju baze.'); st.code(r.text); return pd.DataFrame()
    return pd.DataFrame(r.json())

def insert(d):
    d['user_id']=st.session_state.user_id
    r=requests.post(url(),headers=headers(TOKEN),json=d,timeout=20)
    if r.status_code not in (200,201): st.error('Greška pri spremanju.'); st.code(r.text); return False
    return True

def update(i,d):
    r=requests.patch(f'{url()}?id=eq.{i}',headers=headers(TOKEN),json=d,timeout=20)
    if r.status_code not in (200,204): st.error('Greška pri izmjeni.'); st.code(r.text); return False
    return True

def delete(i):
    r=requests.delete(f'{url()}?id=eq.{i}',headers=headers(TOKEN),timeout=20); return r.status_code in (200,204)

def upload_invoice(order_id,file):
    safe=''.join(c if c.isalnum() or c in '._-' else '_' for c in file.name)
    path=f"{st.session_state.user_id}/{order_id}/{safe}"
    r=requests.post(f'{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}',headers={'apikey':SUPABASE_KEY,'Authorization':f'Bearer {TOKEN}','Content-Type':file.type or 'application/octet-stream','x-upsert':'true'},data=file.getvalue(),timeout=60)
    if r.status_code not in (200,201): st.error('Upload fakture nije uspio.'); st.code(r.text); return False
    return update(order_id,{'faktura_path':path})

def signed_url(path):
    r=requests.post(f'{SUPABASE_URL}/storage/v1/object/sign/{BUCKET}/{path}',headers=headers(TOKEN),json={'expiresIn':3600},timeout=20)
    if r.status_code==200:
        d=r.json(); s=d.get('signedURL') if isinstance(d,dict) else None
        return f"{SUPABASE_URL}/storage/v1{s}" if s else None
    return None

def delete_invoice(path,order_id):
    r=requests.delete(f'{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}',headers=headers(TOKEN),timeout=30)
    if r.status_code not in (200,204): return False
    return update(order_id,{'faktura_path':None})

def late(row):
    if row.get('status') in ('Stiglo','Otkazano'): return False
    try: return pd.to_datetime(row.get('kada_dolazi')).date()<date.today()
    except: return False

def ddate(v):
    try:return pd.to_datetime(v).date()
    except:return date.today()

df=load()
with st.sidebar:
    st.markdown('## ⚡ ORDER HUB')
    st.markdown('<span class="badge">SECURE SESSION</span>',unsafe_allow_html=True)
    st.write(''); st.write(f"👤 **{st.session_state.get('email','')}**")
    st.divider(); st.caption('Tvoji podaci su odvojeni od drugih korisnika.')
    if st.button('🚪 Odjava',use_container_width=True): st.session_state.clear(); st.rerun()

st.markdown("<div class='hero'><div class='eyebrow'>PROCUREMENT DASHBOARD</div><h1>📦 Praćenje narudžbi</h1><div class='muted'>Brz pregled svega što je naručeno, šta stiže i gdje postoji problem.</div></div>",unsafe_allow_html=True)

if len(df):
    active=df[~df.status.isin(['Stiglo','Otkazano'])]; arrived=df[df.status=='Stiglo']; cancelled=df[df.status=='Otkazano']
    metrics=[len(df),len(df[df.status=='Čeka odgovor']),len(df[df.status=='U dolasku']),len(df[df.status=='Problem']),sum(df.apply(late,axis=1))]
else: active=arrived=cancelled=pd.DataFrame(); metrics=[0]*5
m=st.columns(5)
for c,label,val in zip(m,['📦 Ukupno','⏳ Čeka odgovor','🚚 U dolasku','⚠️ Problem','🔴 Kasni'],metrics): c.metric(label,val)

with st.expander('➕ NOVA NARUDŽBA',expanded=True):
    with st.form('new',clear_on_submit=True):
        a,b=st.columns(2)
        with a:
            supplier=st.text_input('Dobavljač',placeholder='npr. Goran, CNC Centar...'); machine=st.text_input('Za koju mašinu',placeholder='npr. Pakerica 1'); ordered=st.text_area('Šta je naručeno',placeholder='Dio, količina, specifikacija...')
        with b:
            od=st.date_input('Datum narudžbe',date.today()); arrival=st.date_input('Kada dolazi',date.today()); status=st.selectbox('Status',STATUS); reply=st.selectbox('Odgovorio',ODG)
        missing=st.text_area('Šta nemaju / zamjena'); note=st.text_area('Napomena')
        if st.form_submit_button('💾 SAČUVAJ NARUDŽBU',use_container_width=True):
            if not supplier.strip() or not ordered.strip(): st.error('Unesi dobavljača i šta je naručeno.')
            elif insert({'dobavljac':supplier.strip(),'masina':machine.strip(),'sta_je_naruceno':ordered.strip(),'datum_narudzbe':od.isoformat(),'kada_dolazi':arrival.isoformat(),'status':status,'odgovorio':reply,'sta_nemaju':missing.strip(),'napomena':note.strip()}): st.success('Narudžba je sačuvana.'); st.rerun()

def show(view,prefix):
    if len(view)==0: st.info('Nema narudžbi u ovoj sekciji.'); return
    q=st.text_input('🔎 Pretraga',placeholder='Dobavljač, mašina, dio...',key=prefix+'q')
    f1,f2=st.columns(2)
    with f1: sup=st.selectbox('Dobavljač',['Svi']+sorted(view.dobavljac.fillna('').astype(str).unique()),key=prefix+'s')
    with f2: sta=st.selectbox('Status',['Svi']+[x for x in STATUS if x in view.status.tolist()],key=prefix+'t')
    x=view.copy()
    if sup!='Svi': x=x[x.dobavljac==sup]
    if sta!='Svi': x=x[x.status==sta]
    if q.strip(): x=x[x.apply(lambda r:q.lower() in ' '.join(r.astype(str)).lower(),axis=1)]
    for _,r in x.iterrows():
        late_tag=' • 🔴 KASNI' if late(r) else ''
        with st.expander(f"#{r.id}  |  {r.dobavljac}  |  {r.sta_je_naruceno}  |  {r.status}{late_tag}"):
            c1,c2,c3=st.columns(3); c1.write(f"**Mašina:** {r.get('masina','')}"); c2.write(f"**Naručeno:** {r.get('datum_narudzbe','')}"); c3.write(f"**Dolazi:** {r.get('kada_dolazi','')}")
            st.write(f"**Šta je naručeno:** {r.get('sta_je_naruceno','')}"); st.write(f"**Odgovorio:** {r.get('odgovorio','')}"); st.write(f"**Šta nemaju:** {r.get('sta_nemaju','')}"); st.write(f"**Napomena:** {r.get('napomena','')}")
            path=r.get('faktura_path')
            if path and str(path)!='nan':
                st.success('📎 Faktura je priložena.')
                su=signed_url(path)
                if su: st.link_button('👁️ Otvori fakturu',su,use_container_width=True)
            else: st.caption('📎 Nema fakture.')
            b1,b2,b3,b4=st.columns(4)
            with b1:
                if r.status!='Stiglo' and st.button('✅ Stiglo',key=f'{prefix}a{r.id}'): update(r.id,{'status':'Stiglo'}); st.rerun()
            with b2:
                if r.status!='Otkazano' and st.button('❌ Otkaži',key=f'{prefix}c{r.id}'): update(r.id,{'status':'Otkazano'}); st.rerun()
            with b3:
                if r.status in ('Stiglo','Otkazano') and st.button('↩️ Vrati aktivno',key=f'{prefix}v{r.id}'): update(r.id,{'status':'Naručeno'}); st.rerun()
            with b4:
                if st.button('🗑️ Obriši',key=f'{prefix}d{r.id}'):
                    if delete(r.id): st.rerun()
            file=st.file_uploader('📎 Dodaj / zamijeni fakturu',type=['pdf','png','jpg','jpeg','webp'],key=f'{prefix}f{r.id}')
            if file is not None and st.button('⬆️ Sačuvaj fakturu',key=f'{prefix}u{r.id}'):
                if upload_invoice(r.id,file): st.success('Faktura je sačuvana.'); st.rerun()
            if path and str(path)!='nan' and st.button('🗑️ Obriši fakturu',key=f'{prefix}df{r.id}'):
                if delete_invoice(path,r.id): st.rerun()

T1,T2,T3=st.tabs(['🟢 AKTIVNE','✅ STIGLO','❌ OTKAZANO'])
with T1: show(active,'act')
with T2: show(arrived,'arr')
with T3: show(cancelled,'can')

st.markdown('---')
with st.expander('✏️ UREDI NARUDŽBU'):
    if len(df)==0: st.info('Nema podataka.')
    else:
        choices={f"#{r.id} • {r.dobavljac} • {r.sta_je_naruceno}":r.id for _,r in df.iterrows()}; label=st.selectbox('Odaberi',list(choices)); rid=choices[label]; r=df[df.id==rid].iloc[0]
        with st.form(f'edit{rid}'):
            a,b=st.columns(2)
            with a: es=st.text_input('Dobavljač',str(r.get('dobavljac',''))); em=st.text_input('Mašina',str(r.get('masina',''))); eo=st.text_area('Šta je naručeno',str(r.get('sta_je_naruceno','')))
            with b:
                ed=st.date_input('Datum narudžbe',ddate(r.get('datum_narudzbe'))); ea=st.date_input('Kada dolazi',ddate(r.get('kada_dolazi'))); est=st.selectbox('Status',STATUS,index=STATUS.index(r.status) if r.status in STATUS else 0); er=st.selectbox('Odgovorio',ODG,index=ODG.index(r.odgovorio) if r.odgovorio in ODG else 0)
            e_missing=st.text_area('Šta nemaju',str(r.get('sta_nemaju',''))); e_note=st.text_area('Napomena',str(r.get('napomena','')))
            if st.form_submit_button('💾 SAČUVAJ IZMJENE',use_container_width=True):
                if update(rid,{'dobavljac':es,'masina':em,'sta_je_naruceno':eo,'datum_narudzbe':ed.isoformat(),'kada_dolazi':ea.isoformat(),'status':est,'odgovorio':er,'sta_nemaju':e_missing,'napomena':e_note}): st.success('Izmjene sačuvane.'); st.rerun()

with st.expander('📥 EXPORT U EXCEL'):
    if len(df):
        ex=df.drop(columns=['user_id','faktura_path'],errors='ignore').copy(); buf=BytesIO()
        with pd.ExcelWriter(buf,engine='openpyxl') as w: ex.to_excel(w,index=False,sheet_name='Narudžbe')
        st.download_button('📊 Preuzmi Excel',buf.getvalue(),'narudzbe_export.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
    else: st.info('Nema podataka.')
