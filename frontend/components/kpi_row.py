"""Animated KPI cards rendered via components.html (allows JavaScript)."""
import streamlit.components.v1 as components


_ACCENT = ["#818cf8", "#06b6d4", "#34d399", "#fbbf24", "#f472b6"]
_ICONS  = ["💰", "📈", "🎯", "🔄", "🌍"]

KpiEntry = tuple[str, str, str]


def render_kpi_row(kpis: list[KpiEntry], is_dark: bool = True) -> None:
    if is_dark:
        bg    = "rgba(15,15,24,0.85)"
        bdr   = "rgba(255,255,255,0.08)"
        lbl_c = "#8888a0"       # muted but VISIBLE on dark bg
        val_c = "#f4f4f8"
        sub_c = "#55556a"
        sh    = "0 8px 32px rgba(0,0,0,0.6)"
        sh_hv = "0 16px 50px rgba(0,0,0,0.75)"
    else:
        bg    = "rgba(255,255,255,0.95)"
        bdr   = "rgba(0,0,0,0.08)"
        lbl_c = "#7070a0"
        val_c = "#09090d"
        sub_c = "#a0a0b8"
        sh    = "0 1px 4px rgba(0,0,0,0.05), 0 0 0 1px rgba(0,0,0,0.06)"
        sh_hv = "0 8px 30px rgba(0,0,0,0.12)"

    cards_html = ""
    for i, (lbl, val, sub) in enumerate(kpis):
        accent = _ACCENT[i % len(_ACCENT)]
        icon   = _ICONS[i % len(_ICONS)]
        cards_html += f"""
        <div class="kc" style="--ac:{accent};animation-delay:{i*0.08:.2f}s">
          <div class="kc-bar"></div>
          <div class="kc-glow"></div>
          <div class="kc-icon">{icon}</div>
          <div class="kc-lbl">{lbl}</div>
          <div class="kc-val" data-raw="{val}">{val}</div>
          <div class="kc-sub">{sub}</div>
        </div>"""

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:'Inter','Segoe UI',system-ui,sans-serif}}
body{{background:transparent;padding:2px 0}}
.row{{display:flex;gap:10px}}
.kc{{
  flex:1; position:relative; overflow:hidden; cursor:default;
  background:{bg};
  border:1px solid {bdr};
  border-radius:16px; padding:18px 16px 14px;
  transition:border-color .25s, transform .25s, box-shadow .25s;
  animation:fadeUp .55s cubic-bezier(.4,0,.2,1) both;
  box-shadow:{sh};
}}
.kc:hover{{
  border-color:var(--ac) !important;
  transform:translateY(-5px) scale(1.01);
  box-shadow:{sh_hv}, 0 0 40px color-mix(in srgb,var(--ac) 18%,transparent);
}}
/* top accent bar */
.kc-bar{{
  position:absolute; top:0; left:0; right:0; height:2px;
  background:linear-gradient(90deg, var(--ac), color-mix(in srgb,var(--ac) 60%,transparent));
  border-radius:16px 16px 0 0;
  box-shadow:0 0 12px var(--ac);
}}
/* glow blob behind card */
.kc-glow{{
  position:absolute; top:-40px; left:-20px; width:120px; height:120px;
  background:radial-gradient(circle, color-mix(in srgb,var(--ac) 15%,transparent), transparent 70%);
  pointer-events:none; transition:opacity .3s; opacity:0;
}}
.kc:hover .kc-glow{{opacity:1}}
.kc-icon{{
  font-size:1.5rem; margin-bottom:8px; display:block;
  filter:drop-shadow(0 0 8px color-mix(in srgb,var(--ac) 55%,transparent));
}}
.kc-lbl{{
  font-size:9px; font-weight:800; letter-spacing:.14em; text-transform:uppercase;
  color:{lbl_c}; margin-bottom:6px;
}}
.kc-val{{
  font-size:1.75rem; font-weight:900; color:{val_c}; line-height:1;
  margin-bottom:5px; transition:color .3s;
  font-variant-numeric:tabular-nums;
}}
.kc:hover .kc-val{{color:var(--ac)}}
.kc-sub{{font-size:9px; color:{sub_c}; font-weight:500; letter-spacing:.02em;}}

@keyframes fadeUp{{from{{opacity:0;transform:translateY(18px)}}to{{opacity:1;transform:translateY(0)}}}}
</style></head><body>
<div class="row">{cards_html}</div>
<script>
(function(){{
  document.querySelectorAll('.kc-val[data-raw]').forEach(function(el,idx){{
    var raw=el.getAttribute('data-raw');
    var pre=(raw.match(/^[^\d]*/)  ||[''])[0];
    var suf=(raw.match(/[^\d.%]*$/) ||[''])[0];
    var num=parseFloat(raw.replace(/[^\d.]/g,''));
    if(isNaN(num)) return;
    var dur=1400,start=null;
    var big=num>=10000;
    function step(ts){{
      if(!start) start=ts;
      var p=Math.min((ts-start)/dur,1);
      var e=1-Math.pow(1-p,4);
      el.textContent=pre+(big?Math.floor(e*num).toLocaleString():+(e*num).toFixed(1))+suf;
      if(p<1) requestAnimationFrame(step); else el.textContent=raw;
    }}
    setTimeout(function(){{requestAnimationFrame(step);}},idx*70+100);
  }});
}})();
</script>
</body></html>"""
    components.html(html, height=130)
