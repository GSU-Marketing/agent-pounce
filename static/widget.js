(function(){
  /* ---------- inject CSS ---------- */
  fetch("/static/widget.css").then(r => r.text()).then(css => {
    const style=document.createElement("style");
    style.innerHTML=css; document.head.appendChild(style);
  });

  /* ---------- DOM skeleton ---------- */
  const wrapper = document.createElement("div"); wrapper.className='ivy-main';

  const bubble = document.createElement("div");
  bubble.className='ivy-circle'; bubble.innerHTML='💬';
  wrapper.appendChild(bubble);

  const popup = document.createElement("div"); popup.className='ivy-popup';
  popup.innerHTML=`
    <div class="ivy-chat-header">
      <span>Hi I’m Pathfinder!</span>
      <button class="ivy-chat-close" aria-label="Close">&times;</button>
    </div>
    <div class="ivy-content">
      <div id="log"></div>
      <form id="form">
        <input id="msg" autocomplete="off" placeholder="How can I help you?">
        <button id="send">Send</button>
      </form>
    </div>`;
  wrapper.appendChild(popup); document.body.appendChild(wrapper);

  /* ---------- elements ---------- */
  const logDiv = popup.querySelector('#log');
  const form   = popup.querySelector('#form');
  const msgBox = popup.querySelector('#msg');

  /* ---------- intro message ---------- */
  const intro = "👋 Welcome to Georgia State’s Graduate Admissions chat! "
              + "Ask me anything — or type *status* to check your application.";
  logDiv.innerHTML = `<div class='bot'>🐾 ${intro}</div>`;

  /* ---------- open / close ---------- */
  bubble.onclick = () => { popup.style.display='flex'; bubble.style.display='none'; };
  popup.querySelector('.ivy-chat-close').onclick = () => {
      popup.style.display='none'; bubble.style.display='flex';
  };

  /* ---------- chat plumbing ---------- */
  form.onsubmit = async e => {
    e.preventDefault();
    const text = msgBox.value.trim();
    if (!text) return;
    logDiv.innerHTML += `<div class='user'>🧑‍🎓 ${text}</div>`;
    msgBox.value=''; logDiv.scrollTop = logDiv.scrollHeight;

    const r  = await fetch('/chat',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:text})
    });
    const js = await r.json();
    const ai = js.choices?.[0]?.message?.content || '[error]';
    logDiv.innerHTML += `<div class='bot'>🐾 ${ai}</div>`;
    logDiv.scrollTop = logDiv.scrollHeight;
  };
})();
