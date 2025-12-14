        (function () {
            const TEMP_JSON = './data/Temperatur.json';   // zu File Temperatur
            const PRESS_JSON = './data/Luftdruck.json';     // zu File Luftdruck
            const tempCtx = document.getElementById('tempChart').getContext('2d');
            const pressCtx = document.getElementById('pressChart').getContext('2d');
            const humiCtx = document.getElementById('humiChart').getContext('2d');

            // Raspinamen normalisieren
            function normalizeDeviceName(raw) {
                if (!raw) return 'unknown';
                const s = String(raw).toLowerCase();
                if (s.includes('red') || s.includes('raspir') || s.includes('raspi-r') || s.includes('raspi_r') || s.includes('raspir')) return 'RaspiR';
                if (s.includes('blue') || s.includes('raspib') || s.includes('raspi-b') || s.includes('raspi_b') || s.includes('raspib')) return 'RaspiB';
                // Testdaten
                if (s.includes('r')) return 'RaspiR';
                if (s.includes('b')) return 'RaspiB';
                return String(raw);
            }

            //!!!
            function toDate(val) {
                if (!val) return null;
                if (val instanceof Date) return val;
                if (typeof val === 'number') {
                    return (String(val).length === 10) ? new Date(val * 1000) : new Date(val);
                }
                // ISO/HTTP
                const dt = luxon.DateTime.fromISO(String(val), { zone: 'local' });
                if (dt.isValid) return dt.toJSDate();
                const dt2 = luxon.DateTime.fromRFC2822(String(val), { zone: 'local' });
                if (dt2.isValid) return dt2.toJSDate();
                const asNum = Number(val);
                if (!Number.isNaN(asNum)) return toDate(asNum);
                const d = new Date(String(val));
                return isNaN(d) ? null : d;
            }

            function extractDateFromString(timestamp){
                return `${timestamp.substr(0,10)} ${timestamp.substr(11,2)}:${timestamp.substr(14,2)}`;
            }

            //empfangene Daten normalisieren (Raspi, Datum, Zeit oder Luftdruck)
            function normalizeRecords(arr) {
                const out = [];
                for (const element of arr) {
                    for (const [k,r] of Object.entries(element)) {
                        //const device = normalizeDeviceName(r.pi || r.device || r.host || r.name || r.id);
                        const device = r.name; // don't normalize name (Testing)
                        const date = toDate(r.time || extractDateFromString(r.timestamp) || r.date || r.ts || r.when);
                        if (!date) continue;
                        const temp = (r.temp !== undefined) ? Number(r.temp) :
                            (r.temperature !== undefined) ? Number(r.temperature) : (Number.isFinite(r.value) ? Number(r.value) : null);
                        const pres = (r.pressure !== undefined) ? Number(r.pressure) :
                            (r.pres !== undefined) ? Number(r.pres) : null;
			const humi = (r.humidity !== undefined) ? Number(r.humidity) : null;
                        out.push({ device, date, temp: Number.isFinite(temp) ? temp : null, pressure: Number.isFinite(pres) ? pres : null ,humi: Number.isFinite(humi) ? humi : null});
                    }
                }
                return out.sort((a, b) => a.date - b.date);
            }

            //sortierte Arrays je Raspi für Temp und Druck
            function buildSeries(records) {
                const tempMap = new Map();
                const presMap = new Map();
                const humiMap = new Map();
                for (const r of records) {
                    if (r.temp !== null) {
                        if (!tempMap.has(r.device)) tempMap.set(r.device, []);
                        tempMap.get(r.device).push({ x: r.date, y: r.temp });
                    }
                    if (r.pressure !== null) {
                        if (!presMap.has(r.device)) presMap.set(r.device, []);
                        presMap.get(r.device).push({ x: r.date, y: r.pressure });
                    }
                    if (r.humidity !== null) {
                        if (!humiMap.has(r.device)) humiMap.set(r.device, []);
                        humiMap.get(r.device).push({ x: r.date, y: r.humi });
                    }
                }
                for (const v of tempMap.values()) v.sort((a, b) => a.x - b.x);
                for (const v of presMap.values()) v.sort((a, b) => a.x - b.x);
                for (const v of humiMap.values()) v.sort((a, b) => a.x - b.x);
                return { tempMap, presMap, humiMap };
            }

            // 5-Minuten-Takt, letzter bekannter Wert wird übernommen
            function resampleTo5Min(map) {
                // Zeit
                let min = Infinity, max = -Infinity;
                for (const arr of map.values()) {
                    if (!arr.length) continue;
                    min = Math.min(min, arr[0].x.getTime());
                    max = Math.max(max, arr[arr.length - 1].x.getTime());
                }
                if (!isFinite(min)) return map;

                const roundDown5 = t => Math.floor(t / (5 * 60 * 1000)) * (5 * 60 * 1000);
                const roundUp5 = t => Math.ceil(t / (5 * 60 * 1000)) * (5 * 60 * 1000);
                const start = roundDown5(min);
                const end = roundUp5(max);

                const result = new Map();
                for (const [device, arr] of map.entries()) {
                    const res = [];
                    let idx = 0;
                    let lastVal = null;
                    for (let t = start; t <= end && idx < arr.length; t += 5 * 60 * 1000) {
                        // TODO adding better stuffing
                        if (arr[idx].x.getTime() > t)continue;
                        while (idx < arr.length && arr[idx].x.getTime() <= t) {
                            lastVal = arr[idx].y;
                            idx++;
                        }
                        if (lastVal !== null) res.push({ x: new Date(t), y: lastVal });
                    }
                    result.set(device, res);
                }
                return result;
            }

            // durchschnittlicher Tageswert
            function aggregateDailyPressure(map) {
                const out = new Map();
                for (const [device, arr] of map.entries()) {
                    const dayMap = new Map();
                    for (const p of arr) {
                        const dt = luxon.DateTime.fromJSDate(p.x);
                        const key = dt.toFormat('yyyy-MM-dd');
                        if (!dayMap.has(key)) dayMap.set(key, { sum: 0, count: 0, millis: dt.startOf('day').toMillis() });
                        const entry = dayMap.get(key);
                        entry.sum += p.y;
                        entry.count += 1;
                    }
                    const series = [];
                    for (const [k, v] of dayMap.entries()) {
                        series.push({ x: new Date(v.millis + 12 * 60 * 60 * 1000), y: Number((v.sum / v.count).toFixed(2)) }); // midday
                    }
                    series.sort((a, b) => a.x - b.x);
                    out.set(device, series);
                }
                return out;
            }

            // TODO adding more colors
            const COLOR = { RaspiR: '#ef4444', RaspiB: '#2563eb' };

            function buildDatasets(map, defaultLabels) {
                const datasets = [];
                // Reihenfolge für korrekte Farben
                const keys = Array.from(map.keys());
                //const ordered = ['RaspiR', 'RaspiB', ...keys.filter(k => k !== 'RaspiR' && k !== 'RaspiB')];
                // this adds colors back?
                const ordered = [ ...keys.filter(k => k !== 'RaspiR' && k !== 'RaspiB')];
                for (const k of ordered) {
                    if (!map.has(k)) continue;
                    datasets.push({
                        label: k,
                        data: map.get(k),
                        borderColor: COLOR[k] || undefined,
                        backgroundColor: COLOR[k] || undefined,
                        tension: 0.2,
                        pointRadius: 2,
                        pointHoverRadius: 5,
                        fill: false
                    });
                }
                return datasets;
            }

            function createClockChart(ctx, datasets, rotatedtext, mesUnit) {
                return new Chart(ctx, {
                    type: 'line',
                    data: { datasets },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: { mode: 'nearest', intersect: false },
                        plugins: {
                            legend: { position: 'top' },
                            tooltip: {
                                callbacks: {
                                    title: items => {
                                        if (!items || !items.length) return '';
                                        const x = items[0].parsed.x;
                                        const dt = (x instanceof Date) ? luxon.DateTime.fromJSDate(x) : luxon.DateTime.fromMillis(Number(x));
                                        return dt.toFormat('HH:mm');
                                    },
                                    label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y} ${mesUnit}`
                                }
                            }
                        },
                        scales: {
                            x: {
                                type: 'time',
                                time: {
                                    unit: 'minute',
                                    stepSize: 5,
                                    displayFormats: { minute: 'HH:mm', hour: 'HH:mm' },
                                    tooltipFormat: 'HH:mm:ss'
                                },
                                ticks: { source: 'auto', maxRotation: 0, autoSkip: true },
                                title: { display: true, text: 'Zeit' }
                            },
                            y: {
                                title: { display: true, text: rotatedtext }
                                //title: { display: true, text: 'Temperatur (°C)' }
                            }
                        }
                    }
                });
            }

            function createPressureChart(ctx, datasets, rotatedtext, mesUnit) {
                return new Chart(ctx, {
                    type: 'line',
                    data: { datasets },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: { mode: 'nearest', intersect: false },
                        plugins: {
                            legend: { position: 'top' },
                            tooltip: {
                                callbacks: {
                                    title: items => {
                                        if (!items || !items.length) return '';
                                        const x = items[0].parsed.x;
                                        const dt = (x instanceof Date) ? luxon.DateTime.fromJSDate(x) : luxon.DateTime.fromMillis(Number(x));
                                        return dt.toFormat('dd.MM.yyyy');
                                    },
                                    label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y} ${mesUnit}`
                                }
                            }
                        },
                        scales: {
                            x: {
                                type: 'time',
                                time: {
                                    unit: 'day',
                                    displayFormats: { day: 'dd.MM.yyyy' }
                                },
                                ticks: { autoSkip: true },
                                title: { display: true, text: 'Datum' }
                            },
                            y: {
                                title: { display: true, text: rotatedtext }
                            }
                        }
                    }
                });
            }

            // holt JSON-Daten von URL
            async function fetchJson(url) {
                try {
                    const res = await fetch(url, { cache: 'no-store' });
                    if (!res.ok) throw new Error('network');
                    const j = await res.json();
                    return j;
                } catch (err) {
                    return null;
                }
            }

            async function loadAndDraw() {
                let tempJson = [];
                let pressJson = tempJson;
                //pressJson = tempJson = await fetchJson("/data/temp.data");
                pressJson = tempJson = await fetchJson(gettingFile);
                //let tempJson = await fetchJson(TEMP_JSON);
                //let pressJson = await fetchJson(PRESS_JSON);

                if (!tempJson && !pressJson) {
                    const combined = await fetchJson('/data/data.json') || await fetchJson('/api/measurements') || null;
                    if (combined) {
                        tempJson = combined;
                        pressJson = combined;
                    } else {
                        // zum Testen Beispiel-Daten
                        tempJson = pressJson = [
                            { pi: 'raspi-red', time: new Date(Date.now() - 1000 * 60 * 60).toISOString(), temp: 19.1, pressure: 1013.2 },
                            { pi: 'raspi-blue', time: new Date(Date.now() - 1000 * 60 * 58).toISOString(), temp: 18.6, pressure: 1013.6 },
                            { pi: 'raspi-red', time: new Date(Date.now() - 1000 * 60 * 55).toISOString(), temp: 19.4, pressure: 1012.8 },
                            { pi: 'raspi-blue', time: new Date(Date.now() - 1000 * 60 * 50).toISOString(), temp: 18.7, pressure: 1013.0 },
                            { pi: 'raspi-red', time: new Date(Date.now() - 1000 * 60 * 10).toISOString(), temp: 20.3, pressure: 1012.4 },
                            { pi: 'raspi-blue', time: new Date().toISOString(), temp: 19.9, pressure: 1012.5 },
                            { pi: 'raspi-red', time: new Date(Date.now() - 24 * 3600 * 1000).toISOString(), temp: 18.7, pressure: 1011.5 },
                            { pi: 'raspi-blue', time: new Date(Date.now() - 24 * 3600 * 1000 + 3600 * 1000).toISOString(), temp: 18.9, pressure: 1011.7 }
                        ];
                    }
                } // */

                // zu einzelnem Array zusammenfassen
                function flatten(maybe) {
                    if (!maybe) return [];
                    if (Array.isArray(maybe)) return maybe;
                    const arr = [];
                    for (const [k, v] of Object.entries(maybe)) {
                        if (Array.isArray(v)) {
                            v.forEach(it => { if (!it.pi) it.pi = k; arr.push(it); });
                        }
                    }
                    return arr;
                }

                const combinedRecords = flatten(tempJson);//.concat(flatten(pressJson));
                const normalized = normalizeRecords(combinedRecords);

                const { tempMap: rawTempMap, presMap: rawPresMap, humiMap: rawHumiMap } = buildSeries(normalized); 

                // Farben und Reihenfolge erzwingen, auch wenn keine Daten vorliegen
                if (!rawTempMap.has('RaspiR')) rawTempMap.set('RaspiR', []);
                if (!rawTempMap.has('RaspiB')) rawTempMap.set('RaspiB', []);
                if (!rawPresMap.has('RaspiR')) rawPresMap.set('RaspiR', []);
                if (!rawPresMap.has('RaspiB')) rawPresMap.set('RaspiB', []);

                // 5-Minuten-Takt Temperatur, letzter bekannter Wert wird übernommen
                const tempMap = resampleTo5Min(rawTempMap);

                // tägliche Aggregation Luftdruck
                //const pressMap = aggregateDailyPressure(rawPresMap);
                const pressMap = resampleTo5Min(rawPresMap);
                //const humidityMap = resampleTo5Min(rawHumiMap);

                // Farbe und Reihenfolge festlegen
                /*
                const tempDatasets = buildDatasets(tempMap);
                const pressDatasets = buildDatasets(pressMap);
                const humiDatasets = buildDatasets(humidityMap);
                /*/
                const tempDatasets = buildDatasets(rawTempMap);
                const pressDatasets = buildDatasets(pressMap);
                //const pressDatasets = buildDatasets(rawPresMap);
                const humiDatasets = buildDatasets(rawHumiMap);
                /* */

                // Charts erstellen
		if(gettingFile.indexOf("akku") != -1){
                    createPressureChart(tempCtx, tempDatasets, "Temperatur (°C)","°C");
                    createPressureChart(pressCtx, pressDatasets, "Luftdruck (hPa)","hPa");
                    createPressureChart(humiCtx, humiDatasets, "Luftfeuchtigkeit (%rH)","%rH");
		} else {
                    createClockChart(tempCtx, tempDatasets, "Temperatur (°C)","°C");
                    createClockChart(pressCtx, pressDatasets, "Luftdruck (hPa)","hPa");
                    createClockChart(humiCtx, humiDatasets, "Luftfeuchtigkeit (%rH)","%rH");
		}
            }

            loadAndDraw();

        })();
