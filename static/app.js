const dropzone = document.querySelector('#dropzone');
const fileInput = document.querySelector('#file-input');
const jobName = document.querySelector('#job-name');
const pageSize = document.querySelector('#page-size');
const strokeCount = document.querySelector('#stroke-count');
const strokeWidth = document.querySelector('#stroke-width');
const strokeWidthLabel = document.querySelector('#stroke-width-label');
const scalePercent = document.querySelector('#scale-percent');
const scalePercentLabel = document.querySelector('#scale-percent-label');
const previewFrame = document.querySelector('#preview-frame');
const emptyPreview = document.querySelector('#empty-preview');
const previewBadge = document.querySelector('#preview-badge');
const previewZoom = document.querySelector('#preview-zoom');
const previewZoomLabel = document.querySelector('#preview-zoom-label');
const downloadLink = document.querySelector('#download-link');
const printButton = document.querySelector('#print-button');
const statusBox = document.querySelector('#status');

let currentJobId = null;
let currentPreviewUrl = null;
let reprocessTimer = null;

function setStatus(message, kind = '') {
  // Semaforo umano: poche parole, utili, niente schermate anni '80.
  statusBox.textContent = message;
  const bootstrapKind = kind === 'ok' ? 'success' : kind === 'error' ? 'danger' : 'secondary';
  statusBox.className = `alert alert-${bootstrapKind} mt-4 mb-0`;
}

function setBusy(isBusy) {
  dropzone.style.pointerEvents = isBusy ? 'none' : '';
  printButton.disabled = isBusy || !currentJobId;
}

function previewUrlWithZoom() {
  if (!currentPreviewUrl) {
    return '';
  }
  return `${currentPreviewUrl}?t=${Date.now()}#zoom=${previewZoom.value}`;
}

function applyPreviewZoom() {
  previewZoomLabel.textContent = `${previewZoom.value}%`;
  if (currentPreviewUrl) {
    previewFrame.src = previewUrlWithZoom();
  }
}

function showPreview(payload) {
  currentPreviewUrl = payload.previewUrl;
  previewFrame.src = previewUrlWithZoom();
  previewFrame.classList.remove('d-none');
  emptyPreview.classList.add('d-none');
  downloadLink.hidden = false;
  downloadLink.href = payload.previewUrl;
  previewBadge.textContent = 'Pronto';
  previewBadge.className = 'badge text-bg-success rounded-pill px-3 py-2';

  jobName.textContent = payload.filename;
  pageSize.textContent = `${payload.pageSize.widthMm} × ${payload.pageSize.heightMm} mm`;
  strokeCount.textContent = `${payload.stats.strokeOperationsSeen} path`;
}

async function uploadPdf(file) {
  if (!file || (file.type && file.type !== 'application/pdf')) {
    setStatus('Carica un PDF valido.', 'error');
    return;
  }

  const form = new FormData();
  form.append('pdf', file);
  form.append('strokeWidth', strokeWidth.value);
  form.append('scalePercent', scalePercent.value);

  currentJobId = null;
  currentPreviewUrl = null;
  setBusy(true);
  setStatus('Elaboro il PDF e rinforzo i tratti sottili…');
  previewBadge.textContent = 'Lavoro';
  previewBadge.className = 'badge text-bg-warning rounded-pill px-3 py-2';

  try {
    const response = await fetch('/upload', { method: 'POST', body: form });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || 'Upload fallito');
    }

    currentJobId = payload.jobId;
    showPreview(payload);
    setStatus('Preview pronta. Controlla il foglio e poi manda in stampa.', 'ok');
  } catch (error) {
    previewBadge.textContent = 'Errore';
    previewBadge.className = 'badge text-bg-danger rounded-pill px-3 py-2';
    setStatus(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

function scheduleReprocess() {
  strokeWidthLabel.textContent = strokeWidth.value;
  scalePercentLabel.textContent = `${scalePercent.value}%`;
  if (!currentJobId) {
    return;
  }
  clearTimeout(reprocessTimer);
  reprocessTimer = setTimeout(reprocessPreview, 350);
}

async function reprocessPreview() {
  if (!currentJobId) {
    return;
  }

  setBusy(true);
  setStatus(`Rigenero preview: tratto ${strokeWidth.value}, scala ${scalePercent.value}%…`);
  previewBadge.textContent = 'Lavoro';
  previewBadge.className = 'badge text-bg-warning rounded-pill px-3 py-2';

  try {
    const response = await fetch(`/jobs/${currentJobId}/stroke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strokeWidth: strokeWidth.value, scalePercent: scalePercent.value }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || 'Rigenerazione fallita');
    }
    showPreview(payload);
    setStatus(`Preview aggiornata: tratto ${strokeWidth.value}, scala ${scalePercent.value}%.`, 'ok');
  } catch (error) {
    previewBadge.textContent = 'Errore';
    previewBadge.className = 'badge text-bg-danger rounded-pill px-3 py-2';
    setStatus(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

async function printCurrentJob() {
  if (!currentJobId) {
    setStatus('Prima carica un PDF.', 'error');
    return;
  }

  setBusy(true);
  setStatus('Invio alla Canon TC-20 sul rullo…');

  try {
    const response = await fetch(`/jobs/${currentJobId}/print`, { method: 'POST' });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.stderr || payload.stdout || 'Stampa fallita');
    }
    setStatus(payload.stdout || 'Job inviato alla stampante.', 'ok');
  } catch (error) {
    setStatus(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener('change', () => uploadPdf(fileInput.files[0]));

for (const eventName of ['dragenter', 'dragover']) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add('drag-over');
  });
}

for (const eventName of ['dragleave', 'drop']) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove('drag-over');
  });
}

dropzone.addEventListener('drop', (event) => {
  uploadPdf(event.dataTransfer.files[0]);
});

strokeWidth.addEventListener('input', scheduleReprocess);
scalePercent.addEventListener('input', scheduleReprocess);
previewZoom.addEventListener('input', applyPreviewZoom);
printButton.addEventListener('click', printCurrentJob);
