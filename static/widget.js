(async()=>{
  /* 1. config, css */
  const cfg = window.POUNCE_CONFIG || {};
  const css = await fetch("/static/widget.css").then(r=>r.text());
  const st  = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  /* 2. expose color vars */
  const root = document.documentElement;
  root.style.setProperty("--pounce-header-bg", cfg.headerBg   || "#0039A6");
  root.style.setProperty("--pounce-header-font", cfg.headerFont || "#FFFFFF");
  root.style.setProperty("--pounce-bubble-bg", cfg.bgColor || "#0039A6");
  root.style.setProperty("--pounce-focus", cfg.focusColor || "#FF0000");

  /* 3. respect exclusion list */
  if ((cfg.excludePaths||[]).some(p=>location.pathname.includes(p))) return;

  /* 4. build DOM */
  const wrap   = document.createElement("div"); wrap.className="pounce-wrap";
  wrap.style[cfg.position?.startsWith("bottom")?"bottom":"top"] = "24px";
  wrap.style[cfg.position?.endsWith("left")?"left":"right"]    = "24px";

  const bubble = document.createElement("div");
  bubble.className = `pounce-bubble ${cfg.shape==="tab"?"tab":"circle"}`;
  bubble.innerHTML = cfg.iconImage
      ? `<img src="${cfg.iconImage}" alt="icon">`
      : `<span style="font-size:28px;color:#fff">${cfg.icon||"💬"}</span>`;
  wrap.appendChild(bubble);

  const pop = document.createElement("div"); pop.className="pounce-popup";
  pop.style.animation = cfg.animation==="slide"
      ? `pounce-slide ${cfg.animationDuration||0.35}s ease ${cfg.animationCount||1}`
      : cfg.animation==="none"
        ? "none"
        : `pounce-bounce ${cfg.animationDuration||0.35}s ease ${cfg.animationCount||1}`;
  pop.innerHTML = `
    <div class="pounce-header">
      <span>${cfg.headerText||"Agent Pounce"}</span>
      <button class="pounce-close" aria-label="Close">&times;</button>
    </div>
    <div style="flex:1;display:flex;flex-direction:column">
      <div id="pounce-log"></div>
      <form id="pounce-form">
        <input id="pounce-msg" placeholder="${cfg.placeholder||"How can I help you?"}">
        <button id="pounce-send">Send</button>
      </form>
    </div>`;
  wrap.appendChild(pop); document.body.appendChild(wrap);

  /* avatar in header */
  if (cfg.avatar){
    const img=document.createElement("img");
    img.src=cfg.avatar; img.alt="avatar";
    img.style="width:28px;height:28px;margin-right:6px;border-radius:50%";
    pop.querySelector(".pounce-header").prepend(img);
  }

  /* intro */
  const log = pop.querySelector("#pounce-log");
  log.innerHTML = `<div class='pounce-bot'>🐾 ${cfg.bodyText||
     "👋 Hi! I’m Agent Pounce, your grad-admissions guru. Ask me anything…"}</div>`;

  /* open/close */
  bubble.onclick = ()=>{pop.style.display="flex";bubble.style.display="none";};
  pop.querySelector(".pounce-close").onclick = ()=>{
    pop.style.display="none"; bubble.style.display="flex";
  };

  /* chat plumbing */
  const form = pop.querySelector("#pounce-form"),
        msg  = pop.querySelector("#pounce-msg");
  form.onsubmit = async e=>{
    e.preventDefault();
    const t = msg.value.trim(); if(!t) return;
    log.innerHTML += `<div class='pounce-user'>🧑‍🎓 ${t}</div>`; msg.value="";
    log.scrollTop = log.scrollHeight;
    const r  = await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
                                   body:JSON.stringify({message:t})});
    const js = await r.json();
    const a  = js.choices?.[0]?.message?.content || '[error]';
    log.innerHTML += `<div class='pounce-bot'>🐾 ${a}</div>`;
    log.scrollTop  = log.scrollHeight;
  };
})();
