const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  NOMBRE_ANTERIOR, resolverCarpetaDatos, describirResolucion,
} = require('../src/carpeta-datos');

function appDataTemporal() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'agronexo-appdata-'));
}

function crearDatos(carpeta, contenido = 'viejo') {
  fs.mkdirSync(path.join(carpeta, 'pgdata'), { recursive: true });
  fs.writeFileSync(path.join(carpeta, 'secretos.json'), JSON.stringify({ contenido }));
  fs.writeFileSync(path.join(carpeta, 'pgdata', 'PG_VERSION'), '16');
}

test('instalación nueva: usa la carpeta nueva sin tocar nada', () => {
  const appData = appDataTemporal();
  const nueva = path.join(appData, 'AgroNexo');
  const resultado = resolverCarpetaDatos(nueva);
  assert.deepEqual(resultado, { carpeta: nueva, accion: 'sin-cambios' });
  assert.equal(describirResolucion(resultado), null);
});

test('renombra la carpeta del prototipo con todo su contenido', () => {
  const appData = appDataTemporal();
  const vieja = path.join(appData, NOMBRE_ANTERIOR);
  const nueva = path.join(appData, 'AgroNexo');
  crearDatos(vieja);

  const resultado = resolverCarpetaDatos(nueva);

  assert.equal(resultado.accion, 'renombrada');
  assert.equal(resultado.carpeta, nueva);
  assert.equal(fs.existsSync(vieja), false);
  assert.equal(fs.readFileSync(path.join(nueva, 'pgdata', 'PG_VERSION'), 'utf8'), '16');
  assert.match(describirResolucion(resultado), /renombrada/);
});

test('si la carpeta nueva ya tiene datos, gana la nueva y la vieja no se toca', () => {
  const appData = appDataTemporal();
  const vieja = path.join(appData, NOMBRE_ANTERIOR);
  const nueva = path.join(appData, 'AgroNexo');
  crearDatos(vieja, 'viejo');
  crearDatos(nueva, 'nuevo');

  const resultado = resolverCarpetaDatos(nueva);

  assert.deepEqual(resultado, { carpeta: nueva, accion: 'sin-cambios' });
  assert.equal(fs.existsSync(path.join(vieja, 'secretos.json')), true);
});

test('si la carpeta nueva existe pero sin datos, sigue usando la vieja', () => {
  const appData = appDataTemporal();
  const vieja = path.join(appData, NOMBRE_ANTERIOR);
  const nueva = path.join(appData, 'AgroNexo');
  crearDatos(vieja);
  fs.mkdirSync(path.join(nueva, 'Local Storage'), { recursive: true });

  const resultado = resolverCarpetaDatos(nueva);

  assert.equal(resultado.accion, 'vieja');
  assert.equal(resultado.carpeta, vieja);
  assert.match(describirResolucion(resultado), /Se sigue usando/);
});

test('una carpeta vieja sin secretos no se considera con datos', () => {
  const appData = appDataTemporal();
  const vieja = path.join(appData, NOMBRE_ANTERIOR);
  const nueva = path.join(appData, 'AgroNexo');
  fs.mkdirSync(path.join(vieja, 'logs'), { recursive: true });

  assert.deepEqual(resolverCarpetaDatos(nueva), { carpeta: nueva, accion: 'sin-cambios' });
  assert.equal(fs.existsSync(vieja), true);
});
