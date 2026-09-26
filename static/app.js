// Map Initialization
const taiwanBounds = L.latLngBounds(
    [20.5, 117.5], // South-West (covers Pratas, Kinmen, etc.)
    [26.5, 123.5]  // North-East (covers Matsu, Pengjia Islet, etc.)
);

const map = L.map('map', {
    zoomControl: false, // We will move zoom control
    minZoom: 7,
    maxBounds: taiwanBounds,
    maxBoundsViscosity: 1.0,
    zoomSnap: 0.1,
    zoomDelta: 0.15,
    wheelPxPerZoomLevel: 120
}).setView([23.7, 120.9], 9);

let baseTileLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19
}).addTo(map);

// (Zoom control now handled at the end)

// --- Custom Controls ---

// 1. Title Panel (Top Left)
const titleControl = L.control({ position: 'topleft' });
titleControl.onAdd = function() {
    const div = L.DomUtil.create('div', 'glass-panel title-panel');
    div.innerHTML = `
        <h1>探索台灣氣象</h1>
        <p>精準觀測 · 即時預警 · 智慧數據</p>
    `;
    return div;
};
titleControl.addTo(map);

// 2. Control Switcher (Top Right)
const switcherControl = L.control({ position: 'topright' });
let dataSourceSelect, displayModeGroup, displayModeSelect, forecastSlotGroup, forecastSlotSelect;

switcherControl.onAdd = function() {
    const div = L.DomUtil.create('div', 'glass-panel control-switcher');
    
    // Stop click events from propagating to the map
    L.DomEvent.disableClickPropagation(div);
    L.DomEvent.disableScrollPropagation(div);

    div.innerHTML = `
        <h3>🎛️ 資料與地圖控制</h3>
        <div class="control-group">
            <button id="dark-mode-btn" style="width: 100%; padding: 1.5rem; font-size: 2.2rem; background: #334155; color: white; border: none; border-radius: 12px; cursor: pointer; font-weight: 800; transition: background 0.2s;">
                🌙 切換深色模式
            </button>
        </div>
        <div class="control-group">
            <button id="sync-btn" style="width: 100%; padding: 1.5rem; font-size: 2.2rem; background: #2563eb; color: white; border: none; border-radius: 12px; cursor: pointer; font-weight: 800; transition: background 0.2s;">
                🔄 立即同步最新資料
            </button>
        </div>
        <div class="control-group">
            <label>📊 地圖資料來源</label>
            <select id="data-source-select">
                <option value="forecast">縣市 36h 天氣預報 (F-C0032-001)</option>
                <option value="station" selected>全台 360+ 測站即時觀測</option>
                <option value="aqi">全台空氣品質即時觀測</option>
            </select>
        </div>
        <div class="control-group" id="display-mode-group">
            <label>👁️ 顯示指標</label>
            <select id="display-mode-select"></select>
        </div>
        <div class="control-group" id="forecast-slot-group" style="display: none;">
            <label>⏱️ 預報時段</label>
            <select id="forecast-slot-select"></select>
        </div>
    `;
    
    // Add Sync Button Listener after a short delay so it's in DOM
    setTimeout(() => {
        const syncBtn = document.getElementById('sync-btn');
        if(syncBtn) {
            syncBtn.addEventListener('click', async () => {
                syncBtn.innerHTML = "⏳ 同步中...";
                syncBtn.disabled = true;
                try {
                    const res = await fetch('/api/sync', { method: 'POST' });
                    if (res.ok) {
                        syncBtn.innerHTML = "✅ 同步成功";
                        await loadAllData(); 
                        renderMap();
                        setTimeout(() => { syncBtn.innerHTML = "🔄 立即同步最新資料"; syncBtn.disabled = false; }, 3000);
                    } else {
                        throw new Error("Sync failed");
                    }
                } catch (e) {
                    syncBtn.innerHTML = "❌ 同步失敗";
                    setTimeout(() => { syncBtn.innerHTML = "🔄 立即同步最新資料"; syncBtn.disabled = false; }, 3000);
                }
            });
        }
        
        const darkBtn = document.getElementById('dark-mode-btn');
        if (darkBtn) {
            darkBtn.addEventListener('click', () => {
                document.body.classList.toggle('dark-mode');
                const isDark = document.body.classList.contains('dark-mode');
                darkBtn.innerHTML = isDark ? "☀️ 切換淺色模式" : "🌙 切換深色模式";
                darkBtn.style.background = isDark ? "#f59e0b" : "#334155";
                darkBtn.style.color = isDark ? "#fff" : "#fff";
                
                // If using Chart.js, you might want to re-render it if the colors are unreadable,
                // but setting grid colors or text colors via CSS often isn't enough for Canvas.
                // We'll let Chart.js default colors handle it for now or re-render if needed.
                if(window.tempChartObj) window.tempChartObj.update();
            });
        }
    }, 100);
    
    return div;
};
switcherControl.addTo(map);

// Get references after DOM insertion
dataSourceSelect = document.getElementById('data-source-select');
displayModeGroup = document.getElementById('display-mode-group');
displayModeSelect = document.getElementById('display-mode-select');
forecastSlotGroup = document.getElementById('forecast-slot-group');
forecastSlotSelect = document.getElementById('forecast-slot-select');

// 3. Legend Panel (Bottom Right)
const legendControl = L.control({ position: 'bottomright' });
legendControl.onAdd = function() {
    const div = L.DomUtil.create('div', 'glass-panel legend-panel');
    div.id = 'legend-container';
    return div;
};
legendControl.addTo(map);
const legendContainer = document.getElementById('legend-container');


// --- Global State ---
let geojsonData = null;
let stationData = [];
let forecastData = [];
let aqiData = [];
let currentLayerGroup = null; // Will initialize after plugins load
let geojsonLayer = null;

// --- Color Functions ---
const getTempColor = (t) => {
    if (t == null || isNaN(t)) return "#94A3B8";
    if (t < 0) return "#004e98"; if (t < 5) return "#3a86ff";
    if (t < 10) return "#00b4d8"; if (t < 15) return "#06d6a0";
    if (t < 20) return "#90be6d"; if (t < 25) return "#f9c74f";
    if (t < 30) return "#f8961e"; if (t < 35) return "#f3722c";
    if (t < 40) return "#d90429"; return "#9d0208";
};
const getRainColor = (p) => {
    if (p == null || isNaN(p)) return "#94A3B8";
    if (p < 20) return "#10B981"; if (p < 50) return "#FBBF24";
    if (p < 80) return "#3B82F6"; return "#8B5CF6";
};
const getPrecipColor = (p) => {
    if (p == null || isNaN(p) || p <= 0) return "#10B981";
    if (p < 5) return "#FBBF24"; if (p < 15) return "#3B82F6";
    return "#8B5CF6";
};
const getAqiColor = (a) => {
    if (a == null || isNaN(a)) return "#94A3B8";
    if (a <= 50) return "#10B981"; if (a <= 100) return "#FBBF24";
    if (a <= 150) return "#F97316"; if (a <= 200) return "#EF4444";
    return "#8B5CF6";
};

// --- Logic ---
async function loadAllData() {
    try {
        const [geoRes, stnRes, fcstRes, aqiRes] = await Promise.all([
            fetch('/api/geojson'), fetch('/api/station'),
            fetch('/api/forecast'), fetch('/api/aqi')
        ]);
        geojsonData = await geoRes.json();
        stationData = await stnRes.json();
        forecastData = await fcstRes.json();
        aqiData = await aqiRes.json();
        
        updateUIState();
        // renderMap() will be called in the .then() block after currentLayerGroup is ready
    } catch (e) {
        console.error("Failed to load data:", e);
    }
}

function updateUIState() {
    const source = dataSourceSelect.value;
    displayModeSelect.innerHTML = '';
    
    if (source === 'forecast') {
        forecastSlotGroup.style.display = 'block';
        displayModeSelect.innerHTML = `
            <option value="temp">氣溫預報 (Temperature)</option>
            <option value="pop">降雨機率 (PoP %)</option>
        `;
        const slots = [...new Set(forecastData.map(d => d.dataDate))].sort();
        forecastSlotSelect.innerHTML = slots.map(s => `<option value="${s}">${s}</option>`).join('');
    } else if (source === 'station') {
        forecastSlotGroup.style.display = 'none';
        displayModeSelect.innerHTML = `
            <option value="temp">即時氣溫 (Temperature)</option>
            <option value="precip">累積雨量 (Precipitation)</option>
        `;
    } else if (source === 'aqi') {
        forecastSlotGroup.style.display = 'none';
        displayModeSelect.innerHTML = `
            <option value="aqi">空氣品質指標 (AQI)</option>
            <option value="pm25">PM2.5 濃度</option>
        `;
    }
    updateLegend();
}

function updateLegend() {
    const mode = displayModeSelect.value;
    let html = '';
    
    if (mode.includes('temp')) {
        html = `
            <div class="legend-title">氣溫色階 (°C)</div>
            <div class="color-bar-container">
                <div class="color-bar" style="background: linear-gradient(to right, #004e98, #00b4d8, #06d6a0, #90be6d, #f9c74f, #f8961e, #d90429, #9d0208);"></div>
                <div class="color-labels"><span><0</span><span>10</span><span>20</span><span>30</span><span>>40</span></div>
            </div>`;
    } else if (mode === 'pop') {
        html = `
            <div class="legend-title">降雨機率色階 (%)</div>
            <div class="color-bar-container">
                <div class="color-bar" style="background: linear-gradient(to right, #10B981, #FBBF24, #3B82F6, #8B5CF6);"></div>
                <div class="color-labels"><span>0%</span><span>30%</span><span>70%</span><span>100%</span></div>
            </div>`;
    } else if (mode === 'precip') {
        html = `
            <div class="legend-title">累積雨量色階 (mm)</div>
            <div class="color-bar-container">
                <div class="color-bar" style="background: linear-gradient(to right, #10B981, #FBBF24, #3B82F6, #8B5CF6);"></div>
                <div class="color-labels"><span>0</span><span>10</span><span>50</span><span>100+</span></div>
            </div>`;
    } else if (mode === 'aqi' || mode === 'pm25') {
        html = `
            <div class="legend-title">空氣品質指標 (AQI)</div>
            <div class="color-bar-container">
                <div class="color-bar" style="background: linear-gradient(to right, #10B981, #FBBF24, #F97316, #EF4444, #8B5CF6);"></div>
                <div class="color-labels"><span>良好</span><span>普通</span><span>敏感</span><span>紅害</span><span>紫爆</span></div>
            </div>`;
    }
    legendContainer.innerHTML = html;
}

function renderMap() {
    currentLayerGroup.clearLayers();
    if (geojsonLayer) {
        map.removeLayer(geojsonLayer);
    }
    
    // Always render Choropleth as background layer
    renderChoropleth();
    
    const source = dataSourceSelect.value;
    // Only render markers for Station or AQI data
    if (source !== 'forecast') {
        renderMarkers();
    }
    
    updateMarkerSizes();
    updateLegend();
    updateSummaryPanel(null);
}

function updateSummaryPanel(countyName = null) {
    const titleEl = document.getElementById('summary-title');
    const contentEl = document.getElementById('summary-content');
    const resetBtn = document.getElementById('summary-reset-btn');
    
    let targetData = [];
    let titleStr = "🌍 全台即時摘要";
    const source = dataSourceSelect.value;
    
    if (source === 'forecast') {
        const slot = forecastSlotSelect.value;
        let data = forecastData.filter(d => d.dataDate === slot);
        if (countyName) {
            data = data.filter(d => (d.regionName || d.locationName) === countyName);
            titleStr = `📌 ${countyName} 預報摘要`;
        }
        targetData = data;
    } else if (source === 'station') {
        let data = stationData;
        if (countyName) {
            data = data.filter(d => d.countyName === countyName);
            titleStr = `📌 ${countyName} 觀測摘要`;
        }
        targetData = data;
    } else if (source === 'aqi') {
        let data = aqiData;
        if (countyName) {
            data = data.filter(d => d.county === countyName);
            titleStr = `📌 ${countyName} 空品摘要`;
        }
        targetData = data;
    }
    
    titleEl.innerText = titleStr;
    resetBtn.style.display = countyName ? 'block' : 'none';
    
    if (targetData.length === 0) {
        contentEl.innerHTML = `<div class="summary-item"><span>無資料</span></div>`;
        return;
    }
    
    let html = '';
    if (source === 'forecast') {
        const minTs = targetData.map(d => d.minT).filter(v => v!=null);
        const maxTs = targetData.map(d => d.maxT).filter(v => v!=null);
        const pops = targetData.map(d => d.pop_num).filter(v => !isNaN(v));
        
        let avgT = 0, highT = "-", lowT = "-", maxPop = "-";
        if (minTs.length && maxTs.length) {
            highT = Math.max(...maxTs) + " °C";
            lowT = Math.min(...minTs) + " °C";
            let sum = 0;
            targetData.forEach(d => { if(d.avgT) sum += d.avgT; });
            avgT = (sum / targetData.filter(d => d.avgT).length).toFixed(1) + " °C";
        }
        if (pops.length) maxPop = Math.max(...pops) + " %";
        
        html = `
            <div class="summary-item"><span>最高溫</span><strong>${highT}</strong></div>
            <div class="summary-item"><span>最低溫</span><strong>${lowT}</strong></div>
            <div class="summary-item"><span>平均溫</span><strong>${avgT}</strong></div>
            <div class="summary-item"><span>最高降雨機率</span><strong>${maxPop}</strong></div>
        `;
    } else if (source === 'station') {
        const temps = targetData.map(d => d.temp).filter(v => v!=null && !isNaN(v));
        const precips = targetData.map(d => d.precipitation).filter(v => v!=null && !isNaN(v));
        
        let highT = "-", lowT = "-", avgT = "-", maxP = "-";
        if (temps.length) {
            highT = Math.max(...temps).toFixed(1) + " °C";
            lowT = Math.min(...temps).toFixed(1) + " °C";
            avgT = (temps.reduce((a,b)=>a+b,0) / temps.length).toFixed(1) + " °C";
        }
        if (precips.length) maxP = Math.max(...precips).toFixed(1) + " mm";
        
        html = `
            <div class="summary-item"><span>最高溫</span><strong>${highT}</strong></div>
            <div class="summary-item"><span>最低溫</span><strong>${lowT}</strong></div>
            <div class="summary-item"><span>平均溫</span><strong>${avgT}</strong></div>
            <div class="summary-item"><span>最大累積雨量</span><strong>${maxP}</strong></div>
            <div class="summary-item"><span>測站總數</span><strong>${targetData.length} 站</strong></div>
        `;
    } else if (source === 'aqi') {
        const aqis = targetData.map(d => d.aqi).filter(v => v!=null && !isNaN(v));
        const pm25s = targetData.map(d => d.pm25).filter(v => v!=null && !isNaN(v));
        
        let maxA = "-", avgA = "-", maxP = "-", avgP = "-";
        if (aqis.length) {
            maxA = Math.max(...aqis);
            avgA = (aqis.reduce((a,b)=>a+b,0) / aqis.length).toFixed(1);
        }
        if (pm25s.length) {
            maxP = Math.max(...pm25s);
            avgP = (pm25s.reduce((a,b)=>a+b,0) / pm25s.length).toFixed(1);
        }
        
        html = `
            <div class="summary-item"><span>最高 AQI</span><strong>${maxA}</strong></div>
            <div class="summary-item"><span>平均 AQI</span><strong>${avgA}</strong></div>
            <div class="summary-item"><span>最高 PM2.5</span><strong>${maxP}</strong></div>
            <div class="summary-item"><span>測站總數</span><strong>${targetData.length} 站</strong></div>
        `;
    }
    contentEl.innerHTML = html;
}

function renderChoropleth() {
    const source = dataSourceSelect.value;
    const mode = displayModeSelect.value;
    const dataMap = {};

    if (source === 'forecast') {
        const slot = forecastSlotSelect.value;
        const slotData = forecastData.filter(d => d.dataDate === slot);
        slotData.forEach(d => { 
            dataMap[d.regionName || d.locationName] = { val: mode === 'temp' ? d.avgT : d.pop_num, row: d }; 
        });
    } else if (source === 'station') {
        const countyGroups = {};
        stationData.forEach(d => {
            if (!d.countyName) return;
            if (!countyGroups[d.countyName]) countyGroups[d.countyName] = [];
            countyGroups[d.countyName].push(mode === 'temp' ? d.temp : d.precipitation);
        });
        for (let c in countyGroups) {
            const vals = countyGroups[c].filter(v => v != null && !isNaN(v));
            if (vals.length > 0) {
                const avg = vals.reduce((a,b)=>a+b, 0) / vals.length;
                dataMap[c] = { val: avg, row: null };
            }
        }
    } else if (source === 'aqi') {
        const countyGroups = {};
        aqiData.forEach(d => {
            if (!d.county) return;
            if (!countyGroups[d.county]) countyGroups[d.county] = [];
            countyGroups[d.county].push(mode === 'aqi' ? d.aqi : d.pm25);
        });
        for (let c in countyGroups) {
            const vals = countyGroups[c].filter(v => v != null && !isNaN(v));
            if (vals.length > 0) {
                const avg = vals.reduce((a,b)=>a+b, 0) / vals.length;
                dataMap[c] = { val: avg, row: null };
            }
        }
    }
    
    geojsonLayer = L.geoJSON(geojsonData, {
        style: function (feature) {
            let countyName = feature.properties.COUNTYNAME.replace(/台/g, '臺');
            if (countyName === "桃園縣") countyName = "桃園市";
            const data = dataMap[countyName];
            let color = "#cbd5e1"; // grey
            if (data != null) {
                if (mode === 'temp') color = getTempColor(data.val);
                else if (mode === 'pop') color = getRainColor(data.val);
                else if (mode === 'precip') color = getPrecipColor(data.val);
                else if (mode === 'aqi' || mode === 'pm25') color = getAqiColor(data.val);
            }
            return { fillColor: color, weight: 1.5, color: 'white', fillOpacity: 0.65 };
        },
        onEachFeature: function (feature, layer) {
            let countyName = feature.properties.COUNTYNAME.replace(/台/g, '臺');
            if (countyName === "桃園縣") countyName = "桃園市";
            const data = dataMap[countyName];
            
            // Render center marker for forecast data
            if (data != null && source === 'forecast') {
                let displayVal = (typeof data.val === 'number') ? data.val.toFixed(1) : data.val;
                if (mode === 'pop') displayVal += '%';
                
                let color = "#cbd5e1";
                if (mode === 'temp') color = getTempColor(data.val);
                else if (mode === 'pop') color = getRainColor(data.val);
                
                // Use turf or layer bounds center
                const center = layer.getBounds().getCenter();
                const bgColor = color + 'B3'; // 70% opacity hex
                const html = `
                    <div class="marker-transparent-circle" style="background-color: ${bgColor}; border-color: ${color};">
                        <span class="marker-circle-val">${displayVal}</span>
                        <span class="marker-circle-name">${countyName}</span>
                    </div>
                `;
                const icon = L.divIcon({ html: html, className: 'custom-div-icon', iconSize: [0, 0] });
                L.marker(center, {icon: icon, interactive: false}).addTo(currentLayerGroup);
            }

            let popupContent = `<div class="popup-title">${countyName}</div>`;
            if (data && data.row && source === 'forecast') {
                const row = data.row;
                popupContent += `
                    <div class="popup-row main-metric"><span>預報氣溫:</span> <strong>${row.minT} - ${row.maxT}°C</strong></div>
                    <div class="popup-row"><span>降雨機率:</span> <strong>${row.pop}%</strong></div>
                    <div class="popup-row"><span>天氣現象:</span> <strong>${row.wx}</strong></div>
                `;
            } else if (data && source !== 'forecast') {
                popupContent += `<div class="popup-row main-metric"><span>全縣平均數值:</span> <strong>${data.val.toFixed(1)}</strong></div>`;
            } else {
                popupContent += `<div class="popup-row"><span>無資料</span></div>`;
            }
            layer.bindPopup(popupContent);
            layer.on('click', function (e) {
                map.flyToBounds(layer.getBounds(), { padding: [50, 50], duration: 1.0 });
                // We can also open the popup right after flying
                setTimeout(() => layer.openPopup(), 1000);
                updateSummaryPanel(countyName);
            });
        }
    }).addTo(map);
}

function renderMarkers() {
    const source = dataSourceSelect.value;
    const mode = displayModeSelect.value;
    let activeData = source === 'station' ? stationData : aqiData;
    
    activeData.forEach(row => {
        let lat = row.lat || row.latitude;
        let lng = row.lng || row.longitude;
        if (!lat || !lng) return;
        
        let valStr = "-", color = "#94a3b8", title = row.stationName || row.sitename;
        
        if (source === 'station') {
            if (mode === 'temp') {
                valStr = row.temp !== null ? row.temp.toFixed(1) : "-";
                color = getTempColor(row.temp);
            } else {
                valStr = row.precipitation !== null ? row.precipitation : "-";
                color = getPrecipColor(row.precipitation);
            }
        } else {
            if (mode === 'aqi') {
                valStr = row.aqi !== null ? row.aqi : "-";
                color = getAqiColor(row.aqi);
            } else {
                valStr = row.pm25 !== null ? row.pm25 : "-";
                color = getAqiColor(row.aqi);
            }
        }
        
        const bgColor = color + 'B3'; // 70% opacity
        const html = `
            <div class="marker-transparent-circle" style="background-color: ${bgColor}; border-color: ${color};">
                <span class="marker-circle-val">${valStr}</span>
                <span class="marker-circle-name">${title}</span>
            </div>`;
            
        const icon = L.divIcon({ html: html, className: 'custom-div-icon', iconSize: [0, 0] });
        let popupContent = `<div class="popup-title">${title}</div>`;
        if (source === 'station') {
            popupContent += `
                <div class="popup-row"><span>氣溫:</span> <strong>${row.temp}°C</strong></div>
                <div class="popup-row"><span>濕度:</span> <strong>${row.humidity}%</strong></div>
                <div class="popup-row"><span>雨量:</span> <strong>${row.precipitation} mm</strong></div>
            `;
        } else {
            popupContent += `
                <div class="popup-row"><span>AQI:</span> <strong>${row.aqi}</strong></div>
                <div class="popup-row"><span>PM2.5:</span> <strong>${row.pm25} μg/m3</strong></div>
            `;
        }
        L.marker([lat, lng], {icon: icon}).bindPopup(popupContent).addTo(currentLayerGroup);
    });
    
    updateMarkerSizes();
}

function updateMarkerSizes() {
    const zoom = map.getZoom();
    // Calculate scale factor based on zoom (base zoom is ~7)
    let scale = 1.0;
    if (zoom >= 9) scale = 1.1;
    if (zoom >= 10) scale = 1.2;
    if (zoom >= 11) scale = 1.35;
    if (zoom >= 12) scale = 1.5;
    if (zoom >= 13) scale = 1.65;
    if (zoom >= 14) scale = 1.8;

    document.querySelectorAll('.marker-transparent-circle').forEach(el => {
        el.style.transform = `translate(-50%, -50%) scale(${scale})`;
    });
    
    // Scale the popups dynamically too
    document.documentElement.style.setProperty('--popup-scale', scale);
}

// --- Region Details Panel (Chart & Table) ---
const regionPanel = document.getElementById('region-panel');
const togglePanelBtn = document.getElementById('toggle-panel-btn');
const regionSelect = document.getElementById('region-select');
const dataTableBody = document.getElementById('data-table-body');
let tempChart = null;

togglePanelBtn.addEventListener('click', () => {
    regionPanel.classList.toggle('collapsed');
    togglePanelBtn.innerText = regionPanel.classList.contains('collapsed') ? '▲' : '▼';
});

function initRegionPanel() {
    if (!forecastData || forecastData.length === 0) return;
    
    // Populate region select (unique locations)
    const locations = [...new Set(forecastData.map(d => d.locationName || d.regionName))].filter(Boolean).sort();
    regionSelect.innerHTML = locations.map(l => `<option value="${l}">${l}</option>`).join('');
    
    // Initial Render
    if (locations.length > 0) {
        updateRegionDetails(locations[0]);
    }
}

regionSelect.addEventListener('change', (e) => {
    updateRegionDetails(e.target.value);
});

function updateRegionDetails(location) {
    const locData = forecastData.filter(d => (d.locationName || d.regionName) === location).sort((a, b) => a.dataDate.localeCompare(b.dataDate));
    
    if (locData.length === 0) return;

    // Update Table
    dataTableBody.innerHTML = locData.map(d => `
        <tr>
            <td>${d.dataDate.substring(5, 16)}</td>
            <td style="color:#2563eb; font-weight:bold;">${d.minT}°C</td>
            <td style="color:#dc2626; font-weight:bold;">${d.maxT}°C</td>
            <td>${d.pop_num}%</td>
        </tr>
    `).join('');

    // Update Chart
    const labels = locData.map(d => d.dataDate.substring(5, 13));
    const minT = locData.map(d => d.minT);
    const maxT = locData.map(d => d.maxT);

    if (tempChart) {
        tempChart.destroy();
    }
    
    const ctx = document.getElementById('tempChart').getContext('2d');
    tempChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '最高溫 (MaxT)',
                    data: maxT,
                    borderColor: '#dc2626',
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                },
                {
                    label: '最低溫 (MinT)',
                    data: minT,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', labels: { font: { size: 18 } } }
            },
            scales: {
                x: { ticks: { font: { size: 16 } } },
                y: { ticks: { font: { size: 16 } } }
            }
        }
    });
}

// --- Event Listeners ---
dataSourceSelect.addEventListener('change', () => { 
    updateUIState(); 
    renderMap();
    if (dataSourceSelect.value === 'forecast') {
        regionPanel.style.display = 'flex';
    } else {
        regionPanel.style.display = 'none';
    }
});
displayModeSelect.addEventListener('change', renderMap);
forecastSlotSelect.addEventListener('change', renderMap);
map.on('zoomend', updateMarkerSizes);

document.getElementById('summary-reset-btn').addEventListener('click', () => {
    map.flyToBounds(taiwanBounds, { padding: [50, 50], duration: 1.0 });
    updateSummaryPanel(null);
});

// Initialize
loadAllData().then(() => {
    currentLayerGroup = L.markerClusterGroup({
        disableClusteringAtZoom: 12,
        spiderfyOnMaxZoom: true,
        maxClusterRadius: 50
    }).addTo(map);
    initRegionPanel();
    
    // Add custom positioned zoom control
    L.control.zoom({ position: 'topleft' }).addTo(map);
    
    
    // We must call renderMap manually here to actually paint the markers because 
    // it was called in loadAllData() before currentLayerGroup was ready!
    renderMap();
});
