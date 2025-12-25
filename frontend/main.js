Cesium.Ion.defaultAccessToken = window.CESIUM_ION_TOKEN || "";

const API_BASE = "http://localhost:8000";

const viewer = new Cesium.Viewer("viewer", {
  animation: true,
  timeline: true,
  baseLayerPicker: false,
});

const idsInput = document.getElementById("ids");
const minutesInput = document.getElementById("minutes");
const stepInput = document.getElementById("step");
const loadButton = document.getElementById("load");
const statusEl = document.getElementById("status");

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? "#ff8a80" : "#f7d154";
}

async function loadSatellites() {
  const ids = idsInput.value.trim();
  const minutes = minutesInput.value.trim();
  const step = stepInput.value.trim();

  if (!ids) {
    setStatus("Enter at least one NORAD ID.", true);
    return;
  }

  setStatus("Loading...");

  try {
    const url = new URL(`${API_BASE}/api/czml`);
    url.searchParams.set("ids", ids);
    url.searchParams.set("minutes", minutes || "90");
    url.searchParams.set("step", step || "10");

    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }

    const data = await response.json();
    if (!data.czml || !Array.isArray(data.czml)) {
      throw new Error("Invalid CZML response.");
    }

    viewer.dataSources.removeAll();
    const dataSource = await Cesium.CzmlDataSource.load(data.czml);
    await viewer.dataSources.add(dataSource);
    await viewer.zoomTo(dataSource);

    if (data.skipped && data.skipped.length > 0) {
      setStatus(`Loaded ${data.used.length}. Skipped: ${data.skipped.join(", ")}`);
    } else {
      setStatus(`Loaded ${data.used.length} satellite(s).`);
    }
  } catch (error) {
    setStatus(error.message || "Failed to load CZML.", true);
  }
}

loadButton.addEventListener("click", loadSatellites);

setStatus("Ready.");
