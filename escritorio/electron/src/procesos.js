const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

function lanzar({ exe, env, archivoLog, registrar }) {
  fs.mkdirSync(path.dirname(archivoLog), { recursive: true });
  const salida = fs.openSync(archivoLog, 'a');
  const hijo = spawn(exe, [], {
    env,
    cwd: path.dirname(archivoLog),
    stdio: ['ignore', salida, salida],
    windowsHide: true,
    shell: false,
  });
  fs.closeSync(salida);
  hijo.on('error', (error) => registrar(`No se pudo lanzar ${path.basename(exe)}: ${error.message}`));
  hijo.on('exit', (codigo) => registrar(`${path.basename(exe)} terminó con código ${codigo}`));
  return hijo;
}

function haTerminado(hijo) {
  return hijo.exitCode !== null || hijo.signalCode !== null;
}

// En Windows no hay señales que cierren un programa con gracia; taskkill /T baja
// también a los procesos hijos para que no queden huérfanos.
function detener(hijo, esperaMs = 10000) {
  if (!hijo || haTerminado(hijo)) return Promise.resolve();
  return new Promise((resolve) => {
    const limite = setTimeout(resolve, esperaMs);
    hijo.once('exit', () => {
      clearTimeout(limite);
      resolve();
    });
    spawn('taskkill', ['/PID', String(hijo.pid), '/T', '/F'], { windowsHide: true, shell: false });
  });
}

async function esperarSalud(url, { timeoutMs, proceso }) {
  const limite = Date.now() + timeoutMs;
  while (Date.now() < limite) {
    if (haTerminado(proceso)) {
      throw new Error('La API se cerró antes de estar lista. Revisá el log.');
    }
    try {
      const respuesta = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (respuesta.ok) return;
    } catch {
      // todavía no responde
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`La API no respondió en ${Math.round(timeoutMs / 1000)} s.`);
}

module.exports = { lanzar, detener, esperarSalud, haTerminado };
