var inp       = document.getElementById('inp');
var msgs      = document.getElementById('msgs');
var sendBtn   = document.getElementById('sendBtn');
var typingInd = document.getElementById('typingIndicator');

// ===== إضافة رسالة =====
function addMsg(html, cls) {
  var d = document.createElement('div');
  d.className = 'msg ' + cls;
  d.innerHTML = html;
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
  return d;
}

// ===== إظهار / إخفاء مؤشر الكتابة =====
function showTyping(show) {
  typingInd.classList.toggle('active', show);
  sendBtn.disabled = show;
  inp.disabled = show;
  if (show) msgs.scrollTop = msgs.scrollHeight;
}

// ===== إرسال السؤال إلى بايثون =====
async function askPython(userQuestion) {
  const response = await fetch("/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question: userQuestion
    })
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "حدث خطأ من الخادم");
  }

  return data.answer;
}

// ===== الدالة الرئيسية للإرسال =====
async function sendMsg() {
  var text = inp.value.trim();

  if (!text || sendBtn.disabled) return;

  addMsg(text, 'user');
  inp.value = '';
  showTyping(true);

  try {
    const answer = await askPython(text);

    showTyping(false);
    addMsg(String(answer).replace(/\n/g, '<br>'), 'bot');

  } catch (err) {
    showTyping(false);
    addMsg(
      'عذراً، حدث خطأ أثناء معالجة طلب سعادتك: ' + err.message,
      'bot'
    );
    console.error(err);
  }
}

// ===== الإرسال بزر Enter =====
inp.addEventListener('keydown', function (e) {
  if (e.key === 'Enter') {
    sendMsg();
  }
});

// ===== ربط الزر في HTML =====
window.sendMsg = sendMsg;