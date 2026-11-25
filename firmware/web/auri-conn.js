// Connessioni del simulatore: rete vera del dispositivo (Wi-Fi o dati), Bluetooth del browser,
// posizione dal GPS del telefono (o dalla rete sul computer). Tutto resta nel browser.
(() => {
  const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  let bt = -1;                                  // -1 non so, 0 no, 1 si'
  try {
    if (navigator.bluetooth && navigator.bluetooth.getAvailability)
      navigator.bluetooth.getAvailability().then(v => { bt = v ? 1 : 0; }).catch(() => { bt = 0; });
    else bt = 0;
  } catch (e) { bt = 0; }

  window.auriNet = () => {
    const online = navigator.onLine !== false;
    const tipo = conn ? (conn.type || '') : '';
    const eff = conn ? (conn.effectiveType || '') : '';
    // tacche: dalla qualita' stimata della rete (4g = piene, 2g = una)
    const bars = !online ? 0 : ({ 'slow-2g': 1, '2g': 1, '3g': 2, '4g': 4 }[eff] || 4);
    return JSON.stringify({ online, tipo, eff, bars, down: conn && conn.downlink ? conn.downlink : 0, bt });
  };

  // posizione: watchPosition finche' qualcuno la chiede, poi si spegne (batteria e privacy)
  let watch = null, pos = null, err = '';
  window.auriLocStart = () => {
    if (watch !== null) return;
    err = '';
    if (!window.isSecureContext) { err = 'no_https'; return; }
    if (!navigator.geolocation) { err = 'no_gps'; return; }
    watch = navigator.geolocation.watchPosition(
      p => { pos = { lat: p.coords.latitude, lon: p.coords.longitude, acc: Math.round(p.coords.accuracy || 0),
                     alt: p.coords.altitude, vel: p.coords.speed }; err = ''; },
      e => { err = e.code === 1 ? 'denied' : 'no_fix'; },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
  };
  window.auriLocStop = () => {
    if (watch !== null) { try { navigator.geolocation.clearWatch(watch); } catch (e) {} }
    watch = null; pos = null;
  };
  window.auriLocPoll = () => JSON.stringify({ on: watch !== null, err, pos });
})();
