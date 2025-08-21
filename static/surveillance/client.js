let running = false;
let track;

async function startCamera() {
  const video = document.getElementById('video');
  const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
  video.srcObject = stream;
  track = stream.getVideoTracks()[0];
  await video.play();
  running = true;
  pushLoop();
}

function stopCamera() {
  running = false;
  if (track) track.stop();
}

async function pushLoop() {
  const token = document.getElementById('token').value;
  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  const targetWidth = 640;
  const ratio = video.videoHeight / video.videoWidth || (9/16);
  canvas.width = targetWidth;
  canvas.height = Math.round(targetWidth * ratio);

  while (running) {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.6);
    const formData = new FormData();
    formData.append('frame_b64', dataUrl);
    formData.append('token', token);
    try {
      await fetch(`/api/upload_frame/`, { method: 'POST', body: formData });
    } catch (e) {
      console.error('Upload error', e);
    }
    await new Promise(r => setTimeout(r, 200));
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('start').onclick = startCamera;
  document.getElementById('stop').onclick = stopCamera;
});
// maps token -> MediaStream
const activeStreams = {};

function startClientStream(token, videoEl, canvasEl) {
  navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    .then(stream => {
      videoEl.srcObject = stream;
      activeStreams[token] = { stream, videoEl, canvasEl };
      // call your existing frame capture/upload logic here per stream
    })
    .catch(console.error);
}

function stopClientStream(videoEl) {
  const token = Object.keys(activeStreams).find(t => activeStreams[t].videoEl === videoEl);
  if (!token) return;
  activeStreams[token].stream.getTracks().forEach(track => track.stop());
  videoEl.srcObject = null;
  delete activeStreams[token];
}
