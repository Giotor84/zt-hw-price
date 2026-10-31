"""Report HTML single-file delle offerte classificate."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import List

from core.models import Offer

CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f6f9;color:#1c2733}
header{background:#0b2a4a;color:#fff;padding:18px 26px}
header h1{margin:0;font-size:20px}
.meta{color:#9fc3e6;font-size:13px;margin-top:4px}
table{border-collapse:collapse;width:96%;margin:20px auto;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.08)}
th,td{padding:10px 12px;border-bottom:1px solid #e3e8ee;font-size:13px;text-align:left}
th{background:#eef3f8;color:#0b2a4a;position:sticky;top:0}
tr:hover{background:#f7fbff}
.best{background:#e7f7ec}
.pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;color:#fff}
.new{background:#1f9d55}.used{background:#c47f17}.refurb{background:#2b6cb0}.open_box{background:#805ad5}.unknown{background:#718096}
.score{font-weight:600;color:#0b2a4a}
a{color:#1a5fb4;text-decoration:none}
.num{text-align:right;font-variant-numeric:tabular-nums}
"""


def _pill(cond: str) -> str:
    return f'<span class="pill {html.escape(cond)}">{html.escape(cond)}</span>'


def render(offers: List[Offer], title: str, out_path: str | Path) -> str:
    rows = []
    for i, o in enumerate(offers):
        cls = ' class="best"' if i == 0 else ""
        lp = o.landed_cost if o.landed_cost is not None else o.price
        rows.append(
            f"<tr{cls}>"
            f"<td>{i+1}</td>"
            f"<td><a href='{html.escape(o.url)}' target='_blank'>{html.escape(o.title[:90])}</a>"
            f"<div class='meta'>{html.escape(o.source)} · {html.escape(o.seller or '')}</div></td>"
            f"<td>{_pill(o.condition)}</td>"
            f"<td class='num'>{o.price:.0f} {html.escape(o.currency)}</td>"
            f"<td class='num'>{lp:.0f} €</td>"
            f"<td class='num'>{o.spec_match:.2f}</td>"
            f"<td class='num'>{o.quality_score or 0:.2f}</td>"
            f"<td class='num score'>{o.total_score or 0:.3f}</td>"
            "</tr>"
        )
    body = "\n".join(rows) or "<tr><td colspan='8'>Nessuna offerta</td></tr>"
    doc = f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>{html.escape(title)}</title><style>{CSS}</style></head>
<body><header><h1>{html.escape(title)}</h1>
<div class="meta">{len(offers)} offerte · costo 'landed' in EUR · ordinato per punteggio totale</div></header>
<table><thead><tr>
<th>#</th><th>Prodotto / venditore</th><th>Cond.</th><th class="num">Prezzo</th>
<th class="num">Landed €</th><th class="num">Spec</th><th class="num">Qualità</th><th class="num">Score</th>
</tr></thead><tbody>{body}</tbody></table></body></html>"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
    return str(out_path)


def render_watch(rows, alerts, ts: str, out_path: str | Path) -> str:
    trs = []
    for pid, cost, target, status, title in rows:
        color = "#c0392b" if status == "ALERT" else ("#1f9d55" if status == "ok" else "#718096")
        cs = f"{cost:.0f} €" if isinstance(cost, (int, float)) else str(cost)
        tg = f"{target:.0f} €" if target else "-"
        trs.append(
            f"<tr><td>{html.escape(str(pid))}</td><td class='num'>{cs}</td>"
            f"<td class='num'>{tg}</td>"
            f"<td style='color:{color};font-weight:600'>{status}</td>"
            f"<td>{html.escape(str(title)[:70])}</td></tr>"
        )
    body = "\n".join(trs) or "<tr><td colspan='5'>watchlist vuota</td></tr>"
    extra = ""
    if alerts:
        lis = "".join(
            f"<li>{html.escape(a[0])}: {a[1]:.0f} € (target {a[2]}) — "
            f"<a href='{html.escape(a[4])}' target='_blank'>link</a></li>"
            for a in alerts
        )
        extra = f"<div class='alert'><h2>{len(alerts)} ALERT</h2><ul>{lis}</ul></div>"
    css = CSS + ".alert{background:#fdecea;border:1px solid #f5b7b1;margin:16px auto;width:94%;padding:10px 18px;border-radius:6px}"
    doc = f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>Watchlist prezzi</title><style>{css}</style></head>
<body><header><h1>Watchlist prezzi AI-hardware</h1>
<div class="meta">aggiornato {html.escape(ts)} · costo 'landed' in EUR</div></header>
{extra}
<table><thead><tr><th>Prodotto</th><th class="num">Miglior €</th><th class="num">Target €</th>
<th>Stato</th><th>Offerta</th></tr></thead><tbody>{body}</tbody></table></body></html>"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
    return str(out_path)


def render_performance(perf: dict, out_path: str | Path) -> str:
    chip = perf.get("chip", {})
    mm = []
    for m in perf.get("models", []):
        lo, hi = m.get("tok_s_low"), m.get("tok_s_high")
        spd = f"{lo:g}" if lo == hi else f"{lo:g}-{hi:g}"
        mm.append(
            "<tr>"
            f"<td>{html.escape(str(m.get('label','')))}</td>"
            f"<td class='num'>{m.get('params_b','')} ({m.get('active_b','')})</td>"
            f"<td>{html.escape(str(m.get('quant','')))}</td>"
            f"<td class='num'>{m.get('size_gb','')} GB</td>"
            f"<td class='num score'>{spd}</td>"
            f"<td>{html.escape(str(m.get('note','')))}</td>"
            "</tr>"
        )
    dd = []
    for d in perf.get("devices", []):
        sw = d.get("sustained_w") or ""
        pw = d.get("peak_w") or ""
        dd.append(
            "<tr>"
            f"<td>{html.escape(str(d.get('name','')))}</td>"
            f"<td class='num'>{sw}W / {pw}W</td>"
            f"<td>{html.escape(str(d.get('power_modes','')))}</td>"
            f"<td>{html.escape(str(d.get('noise','')))}</td>"
            f"<td>{html.escape(str(d.get('expand','')))}</td>"
            f"<td>{html.escape(str(d.get('note','')))}</td>"
            "</tr>"
        )
    chip_meta = (
        f"{html.escape(str(chip.get('name','')))} · {html.escape(str(chip.get('memory','')))} · "
        f"banda {chip.get('bandwidth_theoretical_gbs','?')} GB/s teorici (~{chip.get('bandwidth_real_gbs','?')} reali) · "
        f"VRAM addressable ~{chip.get('vram_addressable_gb','?')} GB"
    )
    doc = f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>Prestazioni - hardware AI (Strix Halo)</title><style>{CSS}</style></head>
<body><header><h1>Prestazioni LLM / termica - mini-PC Ryzen AI Max+ 395</h1>
<div class="meta">{chip_meta}</div></header>
<p style="width:94%;margin:16px auto;color:#5a6b7b;font-size:13px">{html.escape(str(chip.get('note','')))}</p>

<h2 style="width:94%;margin:18px auto 0;color:#0b2a4a">Token/s di riferimento (valgono per QUALSIASI box con questo chip)</h2>
<table><thead><tr><th>Modello</th><th class="num">P (attivi) B</th><th>Quant</th>
<th class="num">Footprint</th><th class="num">tok/s</th><th>Note</th></tr></thead>
<tbody>{''.join(mm)}</tbody></table>

<h2 style="width:94%;margin:18px auto 0;color:#0b2a4a">Differenze per device: TDP sostenuto, termica, rumore, espansione (non il chip)</h2>
<table><thead><tr><th>Device</th><th class="num">Sost./Picco</th><th>Modalita'</th>
<th>Rumore</th><th>Espansione</th><th>Note</th></tr></thead>
<tbody>{''.join(dd)}</tbody></table>
</body></html>"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
    return str(out_path)


DASH_TEMPLATE = r"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>zt-hw-price - Dashboard</title><style>__CSS__
.tabs{display:flex;gap:4px;width:94%;margin:16px auto 0;flex-wrap:wrap}
.tab{padding:9px 16px;border:1px solid #cdd8e3;border-bottom:none;border-radius:8px 8px 0 0;background:#e8eef5;cursor:pointer;font-size:13px;color:#0b2a4a;user-select:none}
.tab.active{background:#fff;font-weight:600}
.panel{display:none;padding-top:6px}
.kpis{display:flex;gap:22px;flex-wrap:wrap;margin-top:6px}
.kpi{font-size:12px;color:#9fc3e6/*overridden below*/}
header .kpi b{color:#fff;font-size:15px}
.controls{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-end;width:94%;margin:16px auto}
.ctl{display:flex;flex-direction:column;gap:4px}
.ctl label{font-size:12px;color:#5a6b7b}
.ctl select,.ctl input{padding:7px 9px;border:1px solid #cdd8e3;border-radius:6px;font-size:13px;min-width:180px}
.filters{display:flex;gap:12px;align-items:flex-end;width:94%;margin:14px auto;flex-wrap:wrap}
#customBox{flex-direction:row;gap:10px;border-left:3px solid #0b2a4a;padding-left:14px}
#customBox .ctl input{min-width:90px}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px;width:94%;margin:6px auto 0}
.card{background:#fff;border-radius:10px;box-shadow:0 1px 6px rgba(0,0,0,.09);padding:16px 18px;border-top:4px solid #0b2a4a}
.card.b{border-top-color:#e8590c}
.card h2{margin:0 0 4px;font-size:16px;color:#0b2a4a}
.card.b h2{color:#c2410c}
.kind{font-size:12px;color:#5a6b7b;margin-bottom:10px}
.big{font-size:30px;font-weight:700;color:#0b2a4a;font-variant-numeric:tabular-nums}
.card.b .big{color:#c2410c}
.big.muted{color:#b3bcc6;font-size:20px}
.sub{font-size:12px;color:#5a6b7b;margin:6px 0 12px}
.ok{background:#1f9d55;color:#fff;border-radius:10px;padding:1px 8px;font-size:11px}
.no{background:#c0392b;color:#fff;border-radius:10px;padding:1px 8px;font-size:11px}
table.kv{width:100%;border-collapse:collapse}
table.kv td{border-bottom:1px solid #eef2f6;padding:6px 4px;font-size:12.5px;vertical-align:top}
table.kv td:first-child{color:#5a6b7b;width:38%}
#cmp{width:94%;margin:22px auto;background:#fff;border-radius:10px;box-shadow:0 1px 6px rgba(0,0,0,.09);padding:16px 18px}
#cmp h3{margin:0 0 14px;color:#0b2a4a}
.barrow{display:grid;grid-template-columns:190px 1fr 1fr;gap:10px;align-items:center;margin:9px 0}
.barlbl{font-size:12px;color:#5a6b7b}
.barwrap{position:relative;background:#eef2f6;border-radius:5px;height:22px;overflow:hidden}
.bar{height:100%}
.bar.a{background:#0b2a4a}
.bar.b{background:#e8590c}
.barwrap span{position:absolute;right:8px;top:2px;font-size:11.5px;color:#333;font-variant-numeric:tabular-nums}
.verdict{width:94%;margin:0 auto 24px;background:#0b2a4a;color:#fff;border-radius:10px;padding:14px 18px;font-size:14px}
.h2s{width:94%;margin:20px auto 0;color:#0b2a4a;font-size:16px}
.alertbox{width:94%;margin:12px auto;background:#fdecea;border:1px solid #f5b7b1;border-radius:8px;padding:10px 18px}
.hint{width:94%;margin:14px auto;color:#5a6b7b;font-size:13px}
.small{font-size:12px;color:#5a6b7b}
@media(max-width:820px){.cards{grid-template-columns:1fr}.barrow{grid-template-columns:110px 1fr 1fr}}
</style></head>
<body>
<header><h1>zt-hw-price - Dashboard unificata</h1>
<div class="meta">Prezzi &amp; offerte · prestazioni LLM (A/B) · watchlist — un'unica pagina, generata dal motore</div>
<div class="kpis">
  <span class="kpi">Offerte: <b id="kpi-off">-</b></span>
  <span class="kpi">Hardware: <b id="kpi-hw">-</b></span>
  <span class="kpi">Modelli: <b id="kpi-md">-</b></span>
  <span class="kpi">Alert watchlist: <b id="kpi-al">-</b></span>
</div></header>

<div class="tabs">
  <div class="tab" data-tab="offerte">Offerte &amp; Prezzi</div>
  <div class="tab" data-tab="prest">Prestazioni (A/B)</div>
  <div class="tab" data-tab="watch">Watchlist</div>
</div>

<!-- ================= PANEL: OFFERTE ================= -->
<section class="panel" id="panel-offerte">
  <div class="filters">
    <div class="ctl"><label>Fonte</label><select id="f_src"></select></div>
    <div class="ctl"><label>Condizione</label><select id="f_cond">
      <option value="">tutte</option><option value="new">new</option><option value="used">used</option>
      <option value="refurb">refurb</option><option value="open_box">open_box</option></select></div>
    <div class="ctl"><label>Cerca nel titolo</label><input id="f_q" type="text" placeholder="es. 128GB, 3090, EVO"></div>
    <div class="ctl"><label>Ordina</label><select id="f_sort">
      <option value="landed_asc">Prezzo landed (crescente)</option>
      <option value="landed_desc">Prezzo landed (decrescente)</option>
      <option value="score">Punteggio</option></select></div>
  </div>
  <p class="small" style="width:94%;margin:0 auto 6px">Mostrate <b id="off_count">0</b> di <b id="off_total">0</b> offerte (max 500 a video). Le offerte provengono dall'ultima ricerca/watch salvata in <code>prezzi.db</code>.</p>
  <table><thead><tr><th>Fonte</th><th>Prodotto</th><th>Cond.</th>
    <th class="num">Prezzo</th><th class="num">Landed €</th><th class="num">Score</th></tr></thead>
    <tbody id="off_tbody"></tbody></table>
</section>

<!-- ================= PANEL: PRESTAZIONI ================= -->
<section class="panel" id="panel-prest">
  <div class="controls">
    <div class="ctl"><label>Hardware A</label><select id="hwA"></select></div>
    <div class="ctl"><label>Hardware B (confronto)</label><select id="hwB"></select></div>
    <div class="ctl"><label>Modello LLM</label><select id="model"></select></div>
    <div class="ctl custom" id="customBox" style="display:none">
      <div class="ctl"><label>Parametri (B)</label><input id="c_params" type="number" value="70" step="1"></div>
      <div class="ctl"><label>Attivi (B)</label><input id="c_active" type="number" value="70" step="1"></div>
      <div class="ctl"><label>Bit/param</label><input id="c_bits" type="number" value="4.5" step="0.25"></div>
    </div>
  </div>
  <div class="cards" id="cards"></div>
  <section id="cmp"></section>
  <div class="verdict" id="verdict"></div>
  <h2 class="h2s">Catalogo hardware (tutte le taglie)</h2>
  <table><thead><tr><th>Hardware</th><th>Gruppo</th><th class="num">Memoria</th><th class="num">Banda</th>
    <th class="num">TDP sost.</th><th>Note</th></tr></thead><tbody id="hw_tbody"></tbody></table>
</section>

<!-- ================= PANEL: WATCHLIST ================= -->
<section class="panel" id="panel-watch">
  <div id="watch_body"></div>
</section>

<script>
const DATA = __DATA__;
const HW = {}; DATA.hardware.forEach(function(h){ HW[h.id]=h; });
const MODELS = DATA.models, REF = DATA.ref_bw, OFFERS = DATA.offers || [], WATCH = DATA.watch || null;
const BITS = {MXFP4:4.25,'Q4_K_M':4.5,'Q8_0':8.5,'Q6_K':6.6,'Q3_K_XL':3.5,BF16:16};
function $(id){ return document.getElementById(id); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
function bitsOf(q){ return BITS[q] || 4.5; }
function fmt(x,d){ d=(d===undefined?1:d); if(!isFinite(x)) return 'n/d';
  return x.toLocaleString('it-IT',{minimumFractionDigits:d,maximumFractionDigits:d}); }
function showTab(name){
  document.querySelectorAll('.tab').forEach(function(t){ t.classList.toggle('active', t.dataset.tab===name); });
  document.querySelectorAll('.panel').forEach(function(p){ p.style.display = (p.id==='panel-'+name)?'block':'none'; });
}

/* ---------- PRESTAZIONI ---------- */
function getModel(){
  const id = $('model').value;
  if(id==='__custom__'){
    const p = parseFloat($('c_params').value)||7, a = parseFloat($('c_active').value)||p, b = parseFloat($('c_bits').value)||4.5;
    return {label:'Personalizzato', params_b:p, active_b:a, quant:(b+' bit'),
            size_gb:p*(b/8)*1.08, perTok_gb:a*(b/8), eff:(a<p*0.8?0.55:0.9), custom:true};
  }
  const m = MODELS.find(function(x){return x.id===id;}) || MODELS[0];
  const moe = m.active_b < m.params_b*0.8;
  return {label:m.label, params_b:m.params_b, active_b:m.active_b, quant:m.quant, size_gb:m.size_gb,
          perTok_gb:m.active_b*(bitsOf(m.quant))/8, eff:(moe?0.55:0.9), custom:false, model:m};
}
function tokFor(mw, hw){
  if(!mw.custom){ const k = hw.bandwidth_gbs/REF; return [mw.model.tok_s_low*k, mw.model.tok_s_high*k]; }
  const t = hw.bandwidth_gbs/mw.perTok_gb*mw.eff; return [t*0.9, t*1.1];
}
function fits(mw, hw){ return mw.size_gb <= hw.usable_gb; }
function card(k, hw, mw){
  const f = fits(mw, hw), side=(k==='A'?'a':'b'), tk = f?tokFor(mw,hw):null;
  const range = tk ? (Math.abs(tk[1]-tk[0])>1 ? (fmt(tk[0],0)+'–'+fmt(tk[1],0)) : fmt(tk[0],0)) : '';
  const tokTxt = f ? (range+' t/s') : 'spill (non entra)';
  const badge = f ? '<span class="ok">entra in memoria</span>' : '<span class="no">NON entra</span>';
  return '<div class="card '+side+'"><h2>'+k+'. '+esc(hw.name)+'</h2>'+
    '<div class="kind">'+(hw.kind==='gpu'?'GPU dedicata':'memoria unificata')+' · '+badge+'</div>'+
    '<div class="big'+(f?'':' muted')+'">'+tokTxt+'</div>'+
    '<div class="sub">generazione stimata su <b>'+esc(mw.label)+'</b> ('+fmt(mw.size_gb,0)+' GB pesi, '+esc(mw.quant)+')</div>'+
    '<table class="kv">'+
      '<tr><td>Memoria</td><td>'+hw.memory_gb+' GB (usabile '+hw.usable_gb+')</td></tr>'+
      '<tr><td>Banda</td><td>'+hw.bandwidth_gbs+' GB/s</td></tr>'+
      '<tr><td>TDP sostenuto</td><td>'+hw.tdp_sustained_w+' W (picco '+hw.tdp_peak_w+')</td></tr>'+
      '<tr><td>Rumore</td><td>'+esc(hw.noise_dba||'-')+'</td></tr>'+
      '<tr><td>Espansione</td><td>'+esc(hw.expand||'-')+'</td></tr>'+
      '<tr><td>Note</td><td>'+esc(hw.note||'')+'</td></tr>'+
    '</table></div>';
}
function bar(label, a, b, unit){
  const max = Math.max(a||0,b||0)||1;
  return '<div class="barrow"><div class="barlbl">'+label+'</div>'+
    '<div class="barwrap"><div class="bar a" style="width:'+((a||0)/max*100)+'%"></div><span>'+fmt(a,0)+unit+'</span></div>'+
    '<div class="barwrap"><div class="bar b" style="width:'+((b||0)/max*100)+'%"></div><span>'+fmt(b,0)+unit+'</span></div></div>';
}
function updatePerf(){
  const hwA=HW[$('hwA').value], hwB=HW[$('hwB').value], mw=getModel();
  $('customBox').style.display = mw.custom?'flex':'none';
  $('cards').innerHTML = card('A',hwA,mw)+card('B',hwB,mw);
  const fA=fits(mw,hwA), fB=fits(mw,hwB);
  const tA=fA?tokFor(mw,hwA):[0,0], tB=fB?tokFor(mw,hwB):[0,0];
  const mid=function(t){return (t[0]+t[1])/2;};
  let h='<h3>Confronto A (navy) vs B (arancione)</h3>';
  h+=bar('Generazione (t/s)', fA?mid(tA):0, fB?mid(tB):0, ' t/s');
  h+=bar('Banda memoria (GB/s)', hwA.bandwidth_gbs, hwB.bandwidth_gbs, '');
  h+=bar('TDP sostenuto (W)', hwA.tdp_sustained_w, hwB.tdp_sustained_w, '');
  h+=bar('Memoria usabile (GB)', hwA.usable_gb, hwB.usable_gb, '');
  $('cmp').innerHTML=h;
  let v;
  if(!fA && !fB){ v='Nessuno dei due fa entrare '+mw.label+' ('+fmt(mw.size_gb,0)+' GB).'; }
  else if(fA && !fB){ v=hwA.name+' fa girare '+mw.label+'; '+hwB.name+' NO ('+fmt(mw.size_gb,0)+' GB > '+hwB.usable_gb+' usabili) -> spill in RAM.'; }
  else if(!fA && fB){ v=hwB.name+' fa girare '+mw.label+'; '+hwA.name+' NO (spill in RAM).'; }
  else { const ra=mid(tB)/mid(tA);
    if(Math.abs(ra-1)<0.05){ v='Su '+mw.label+' i due sono <b>equivalenti</b> (~'+fmt(mid(tA),0)+' t/s): stessa banda.'; }
    else { v='Su '+mw.label+': <b>'+(ra>1?'B':'A')+'</b> è '+fmt(Math.max(ra,1/ra),1)+'x più veloce (~'+fmt(mid(tA),0)+' vs '+fmt(mid(tB),0)+' t/s).'; }
  }
  $('verdict').innerHTML=v;
}
function hwOptions(){
  const fams={}, order=[];
  DATA.hardware.forEach(function(h){ const f=h.family||'Altro'; if(!fams[f]){fams[f]=[];order.push(f);} fams[f].push(h); });
  return order.map(function(f){ return '<optgroup label="'+esc(f)+'">'+
    fams[f].map(function(h){return '<option value="'+h.id+'">'+esc(h.name)+'</option>';}).join('')+'</optgroup>'; }).join('');
}
function renderCatalog(){
  $('hw_tbody').innerHTML = DATA.hardware.map(function(h){
    return '<tr><td>'+esc(h.name)+'</td><td class="small">'+esc(h.family||'')+'</td>'+
      '<td class="num">'+h.memory_gb+' GB<br><span class="small">usab. '+h.usable_gb+'</span></td>'+
      '<td class="num">'+h.bandwidth_gbs+' GB/s</td><td class="num">'+h.tdp_sustained_w+' W</td>'+
      '<td class="small">'+esc(h.note||'')+'</td></tr>';
  }).join('');
}

/* ---------- OFFERTE ---------- */
function initOffers(){
  const srcs = Array.from(new Set(OFFERS.map(function(o){return o.source;}))).sort();
  $('f_src').innerHTML = '<option value="">tutte</option>'+srcs.map(function(s){return '<option value="'+esc(s)+'">'+esc(s)+'</option>';}).join('');
  $('off_total').textContent = OFFERS.length;
}
function renderOffers(){
  const src=$('f_src').value, cond=$('f_cond').value, q=$('f_q').value.toLowerCase(), sort=$('f_sort').value;
  let rows = OFFERS.filter(function(o){
    if(src && o.source!==src) return false;
    if(cond && o.condition!==cond) return false;
    if(q && !((o.title||'').toLowerCase().indexOf(q)>=0)) return false;
    return true;
  });
  rows.sort(function(a,b){ return (a.landed_cost==null?1e12:a.landed_cost)-(b.landed_cost==null?1e12:b.landed_cost); });
  if(sort==='landed_desc') rows.reverse();
  else if(sort==='score') rows.sort(function(a,b){ return (b.total_score||0)-(a.total_score||0); });
  $('off_count').textContent = rows.length;
  $('off_tbody').innerHTML = rows.slice(0,500).map(function(o){
    const lc = (o.landed_cost!=null)? fmt(o.landed_cost,0)+' €' : '-';
    const pr = (o.price!=null)? fmt(o.price,0)+' '+esc(o.currency||'') : '';
    return '<tr><td>'+esc(o.source)+'</td>'+
      '<td><a href="'+esc(o.url)+'" target="_blank">'+esc((o.title||'').slice(0,95))+'</a></td>'+
      '<td>'+esc(o.condition||'')+'</td><td class="num">'+pr+'</td>'+
      '<td class="num">'+lc+'</td><td class="num score">'+(o.total_score!=null?fmt(o.total_score,3):'')+'</td></tr>';
  }).join('');
}

/* ---------- WATCHLIST ---------- */
function renderWatch(){
  if(!WATCH){ $('watch_body').innerHTML = '<p class="hint">Snapshot assente. Esegui il watch (zt-hw-price.bat o <code>cli.py watch</code>) per popolare questa sezione.</p>'; return; }
  let h = '<p class="small" style="width:94%;margin:12px auto">aggiornato '+esc(WATCH.ts||'')+'</p>';
  if(WATCH.alerts && WATCH.alerts.length){
    h += '<div class="alertbox"><b>'+WATCH.alerts.length+' ALERT</b><ul>'+WATCH.alerts.map(function(a){
      return '<li>'+esc(String(a[0]))+': '+fmt(a[1],0)+' € (target '+a[2]+') — <a href="'+esc(a[4])+'" target="_blank">link</a></li>';
    }).join('')+'</ul></div>';
  }
  h += '<table><thead><tr><th>Prodotto</th><th class="num">Migliore €</th><th class="num">Target €</th><th>Stato</th><th>Offerta</th></tr></thead><tbody>';
  h += (WATCH.rows||[]).map(function(r){
    const cs = (typeof r[1]==='number')? fmt(r[1],0)+' €' : esc(String(r[1]));
    const color = r[3]==='ALERT'?'#c0392b':(r[3]==='ok'?'#1f9d55':'#718096');
    return '<tr><td>'+esc(String(r[0]))+'</td><td class="num">'+cs+'</td>'+
      '<td class="num">'+(r[2]?fmt(r[2],0)+' €':'-')+'</td>'+
      '<td style="color:'+color+';font-weight:600">'+esc(String(r[3]))+'</td>'+
      '<td>'+esc(String(r[4]||'').slice(0,70))+'</td></tr>';
  }).join('');
  h += '</tbody></table>';
  $('watch_body').innerHTML = h;
}

function init(){
  $('hwA').innerHTML = hwOptions(); $('hwB').innerHTML = hwOptions();
  $('model').innerHTML = MODELS.map(function(m){return '<option value="'+m.id+'">'+esc(m.label)+'</option>';}).join('') +
    '<option value="__custom__">— personalizzato —</option>';
  $('hwA').value='ms-s1-max'; $('hwB').value='rtx-5090'; $('model').value='qwen3-30b-a3b';
  ['hwA','hwB','model','c_params','c_active','c_bits'].forEach(function(id){ $(id).addEventListener('input', updatePerf); });
  updatePerf(); renderCatalog();

  initOffers();
  ['f_src','f_cond','f_sort'].forEach(function(id){ $(id).addEventListener('change', renderOffers); });
  $('f_q').addEventListener('input', renderOffers);
  renderOffers();
  renderWatch();

  document.querySelectorAll('.tab').forEach(function(t){ t.addEventListener('click', function(){ showTab(t.dataset.tab); }); });

  $('kpi-off').textContent = OFFERS.length;
  $('kpi-hw').textContent = DATA.hardware.length;
  $('kpi-md').textContent = MODELS.length;
  $('kpi-al').textContent = (WATCH && WATCH.alerts) ? WATCH.alerts.length : 0;
  showTab('offerte');
}
init();
</script></body></html>"""


def render_dashboard(models, hardware, ref_bw, offers, watch, out_path: str | Path) -> str:
    data = {"models": models, "hardware": hardware, "ref_bw": ref_bw,
            "offers": offers or [], "watch": watch}
    doc = DASH_TEMPLATE.replace("__CSS__", CSS).replace("__DATA__", json.dumps(data, ensure_ascii=False))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
    return str(out_path)
