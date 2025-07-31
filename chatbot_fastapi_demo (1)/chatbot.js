(() => {
  const chatBox = document.createElement("div");
  chatBox.style.position = "fixed";
  chatBox.style.bottom = "20px";
  chatBox.style.right = "20px";
  chatBox.style.width = "320px";
  chatBox.style.height = "440px";
  chatBox.style.border = "1px solid #ccc";
  chatBox.style.borderRadius = "8px";
  chatBox.style.backgroundColor = "#fff";
  chatBox.style.zIndex = "9999";
  chatBox.style.boxShadow = "0 4px 10px rgba(0,0,0,0.1)";
  chatBox.innerHTML = `
    <div style="background:#002F6C;color:white;padding:10px;border-radius:8px 8px 0 0;">GSU GradBot</div>
    <div id="chat" style="padding:10px;height:340px;overflow-y:auto;font-family:sans-serif;font-size:14px;"></div>
    <textarea id="userInput" style="width:100%;height:50px;border:none;padding:10px;resize:none;"></textarea>
  `;

  document.body.appendChild(chatBox);

  const chat = document.getElementById("chat");
  const input = document.getElementById("userInput");

  input.addEventListener("keydown", async (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const userMessage = input.value.trim();
      if (!userMessage) return;
      chat.innerHTML += `<div><b>You:</b> ${userMessage}</div>`;
      input.value = "";
      const res = await fetch("https://your-render-url.onrender.com/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage })
      });
      const data = await res.json();
      chat.innerHTML += `<div><b>GradBot:</b> ${data.response || "Sorry, something went wrong."}</div>`;
      chat.scrollTop = chat.scrollHeight;
    }
  });
})();
