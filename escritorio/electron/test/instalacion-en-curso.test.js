const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  ARCHIVO, VENCE_MS, marcarInstalacion, instalacionEnCurso,
} = require('../src/instalacion-en-curso');

function carpetaTemporal() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'agronexo-instalando-'));
}

test('sin marca se arranca normalmente', () => {
  assert.equal(instalacionEnCurso(carpetaTemporal(), '4.0.0'), null);
});

test('abierta con la versión vieja mientras se instala la nueva: hay que esperar', () => {
  const carpeta = carpetaTemporal();
  marcarInstalacion(carpeta, '4.0.1', 1000);
  assert.equal(instalacionEnCurso(carpeta, '4.0.0', 1000 + 30000), '4.0.1');
  assert.equal(fs.existsSync(path.join(carpeta, ARCHIVO)), true);
});

test('la versión nueva ya instalada borra la marca y arranca', () => {
  const carpeta = carpetaTemporal();
  marcarInstalacion(carpeta, '4.0.1', 1000);
  assert.equal(instalacionEnCurso(carpeta, '4.0.1', 1000 + 60000), null);
  assert.equal(fs.existsSync(path.join(carpeta, ARCHIVO)), false);
});

test('si la instalación no terminó en 10 minutos se deja abrir la versión que haya', () => {
  const carpeta = carpetaTemporal();
  marcarInstalacion(carpeta, '4.0.1', 1000);
  assert.equal(instalacionEnCurso(carpeta, '4.0.0', 1000 + VENCE_MS), null);
  assert.equal(fs.existsSync(path.join(carpeta, ARCHIVO)), false);
});

test('una marca rota no bloquea el arranque', () => {
  const carpeta = carpetaTemporal();
  fs.writeFileSync(path.join(carpeta, ARCHIVO), '{roto');
  assert.equal(instalacionEnCurso(carpeta, '4.0.0'), null);
  assert.equal(fs.existsSync(path.join(carpeta, ARCHIVO)), false);
});
