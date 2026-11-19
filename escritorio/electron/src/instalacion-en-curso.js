const fs = require('node:fs');
const path = require('node:path');

// El instalador de una actualización corre en silencio y tarda uno o dos minutos. Si en ese
// rato se abre la app, arrancaría con archivos a medio reemplazar (o sin el motor). Antes de
// instalar se deja esta marca; la versión nueva la borra al abrir.
const ARCHIVO = 'actualizando.json';
// Pasado este tiempo se asume que la instalación falló y se deja abrir la versión que haya.
const VENCE_MS = 10 * 60 * 1000;

function marcarInstalacion(carpetaDatos, version, ahora = Date.now()) {
  fs.writeFileSync(path.join(carpetaDatos, ARCHIVO), JSON.stringify({ version, desde: ahora }));
}

// Devuelve la versión que se está instalando si hay que esperar, o null si se puede arrancar.
function instalacionEnCurso(carpetaDatos, versionActual, ahora = Date.now()) {
  const archivo = path.join(carpetaDatos, ARCHIVO);
  let marca;
  try {
    marca = JSON.parse(fs.readFileSync(archivo, 'utf8'));
  } catch {
    fs.rmSync(archivo, { force: true });
    return null;
  }
  const termino = marca.version === versionActual;
  const vencida = !(ahora - marca.desde < VENCE_MS);
  if (termino || vencida) {
    fs.rmSync(archivo, { force: true });
    return null;
  }
  return marca.version;
}

module.exports = { ARCHIVO, VENCE_MS, marcarInstalacion, instalacionEnCurso };
