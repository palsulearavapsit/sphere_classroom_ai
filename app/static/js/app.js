// Helper function to get CSRF token
function getCSRFToken() {
  const meta = document.querySelector('meta[name="csrf-token"]')
  if (meta) return meta.getAttribute('content')
  // Fallback: try to get from cookie
  const cookies = document.cookie.split(';')
  for (let cookie of cookies) {
    const [name, value] = cookie.trim().split('=')
    if (name === 'csrf_token') return value
  }
  return ''
}

// Helper to create headers with CSRF token
function getHeaders() {
  return {
    "Content-Type": "application/json",
    "X-CSRFToken": getCSRFToken()
  }
}

async function tutorSend() {
  const t = document.getElementById("tutor-input").value.trim()
  if (!t) return
  
  // Show loading status
  const statusEl = document.getElementById("context-status")
  const replyEl = document.getElementById("tutor-reply")
  
  if (statusEl) statusEl.innerText = "🔍 Searching documents for context..."
  if (replyEl) replyEl.innerText = "💭 Thinking..."
  
  const r = await fetch("/tutor/chat", {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ message: t }),
  })
  const j = await r.json()
  
  // Update context status
  if (statusEl) {
    if (j.rag_results_count > 0) {
      statusEl.innerText = `📚 Used ${j.rag_results_count} document(s) for context`
      statusEl.style.color = "#2e7d32"
    } else {
      statusEl.innerText = "💡 No relevant documents found, using general knowledge"
      statusEl.style.color = "#666"
    }
  }
  
  document.getElementById("tutor-reply").innerText = j.reply || "No reply"
  
  // Clear input
  document.getElementById("tutor-input").value = ""
}
async function tutorSave() {
  const r = await fetch("/tutor/save", { 
    method: "POST",
    headers: getHeaders()
  })
  const j = await r.json()
  alert("Saved session #" + j.session_id)
}
function _csv(s) {
  return s
    .split(",")
    .map((v) => Number.parseFloat(v.trim()))
    .filter((v) => !isNaN(v))
}
async function linearFit() {
  const x = _csv(document.getElementById("fit-x").value)
  const y = _csv(document.getElementById("fit-y").value)
  const r = await fetch("/data/fit", {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ x, y, kind: "linear" }),
  })
  document.getElementById("fit-out").innerText = JSON.stringify(await r.json(), null, 2)
}
async function propagate() {
  const formula = document.getElementById("formula").value
  const values = JSON.parse(document.getElementById("values").value || "{}")
  const errors = JSON.parse(document.getElementById("errors").value || "{}")
  const r = await fetch("/data/propagate", {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ formula, values, errors }),
  })
  document.getElementById("prop-out").innerText = JSON.stringify(await r.json(), null, 2)
}
async function analyze() {
  const arr = document
    .getElementById("arr")
    .value.split(",")
    .map((s) => Number.parseFloat(s.trim()))
    .filter((n) => !isNaN(n))
  const r = await fetch("/data/analyze", {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ data: arr }),
  })
  document.getElementById("ana-out").innerText = JSON.stringify(await r.json(), null, 2)
}
async function submitAssessment() {
  const root = document.getElementById("assessment")
  const testId = Number.parseInt(root.dataset.testid)
  const qs = root.querySelectorAll(".q")
  const answers = []
  qs.forEach((q, i) => {
    const checked = q.querySelector('input[type="radio"]:checked')
    answers.push(checked ? checked.value : "")
  })
  const r = await fetch("/assessments/submit/" + testId, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ answers }),
  })
  const j = await r.json()
  document.getElementById("score").innerText = "Score: " + (j.score?.toFixed(1) ?? "N/A")
}
async function reindex() {
  const r = await fetch("/rag/reindex", { 
    method: "POST",
    headers: getHeaders()
  })
  alert("Reindex: " + JSON.stringify(await r.json()))
}
async function ragSearch() {
  const q = document.getElementById("rag-q").value
  const r = await fetch("/rag/search", {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ q }),
  })
  document.getElementById("rag-out").innerText = JSON.stringify(await r.json(), null, 2)
}

async function uploadOCR() {
  const fileInput = document.getElementById("ocr-file")
  const file = fileInput.files[0]
  if (!file) {
    alert("Please select an image file first")
    return
  }
  
  const formData = new FormData()
  formData.append("image", file)
  
  const r = await fetch("/ocr/upload", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCSRFToken()
    },
    body: formData
  })
  
  if (r.ok) {
    const j = await r.json()
    document.getElementById("ocr-out").innerText = j.text || "No text extracted"
  } else {
    const err = await r.json()
    document.getElementById("ocr-out").innerText = "Error: " + (err.error || "Upload failed")
  }
}

