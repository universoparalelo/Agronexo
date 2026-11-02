const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  carpetaCopias, leerAviso, borrarAviso, mensajeDelAviso, describirFallo,
} = require('../src/copias');
const { entornoMotor } = require('../src/entorno');

function carpetaTemporal() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'agronexo-copias-'));
}

test('las copias van en una subcarpeta de la carpeta de datos', () => {
  assert.equal(carpetaCopias(path.join('datos', 'app')), path.join('datos', 'app', 'copias'));
});

test('sin aviso, leerAviso devuelve null', () => {
  assert.equal(leerAviso(carpetaTemporal()), null);
});

test('un archivo roto no se toma como aviso', () => {
  const carpeta = carpetaTemporal();
  fs.writeFileSync(path.join(carpeta, 'actualizacion-fallida.json'), '{no es json');
  assert.equal(leerAviso(carpeta), null);
});

test('lee el aviso que dejó la API y lo borra cuando el arranque sale bien', () => {
  const carpeta = carpetaTemporal();
  fs.writeFileSync(
    path.join(carpeta, 'actualizacion-fallida.json'),
    JSON.stringify({ motivo: 'migracion', restaurada: true }),
  );
  assert.deepEqual(leerAviso(carpeta), { motivo: 'migracion', restaurada: true });
  borrarAviso(carpeta);
  assert.equal(leerAviso(carpeta), null);
  borrarAviso(carpeta);
});

test('el mensaje depende de lo que pasó', () => {
  const carpeta = path.join('datos', 'copias');
  assert.match(mensajeDelAviso({ motivo: 'migracion', restaurada: true }, carpeta), /como estaban/);
  assert.match(mensajeDelAviso({ motivo: 'migracion', restaurada: true }, carpeta), /versión anterior/);
  assert.match(mensajeDelAviso({ motivo: 'sin_copia', restaurada: false }, carpeta), /No se tocó tu base/);
  const sinRestaurar = mensajeDelAviso({ motivo: 'migracion', restaurada: false }, carpeta);
  assert.match(sinRestaurar, /No borres nada/);
  assert.ok(sinRestaurar.includes(carpeta));
});

test('el motor recibe dónde está pg_dump y dónde guardar la copia', () => {
  const env = entornoMotor({
    secretos: { pgPassword: 'a', jwtSecret: 'b' },
    puertoPg: 1, puertoApi: 2, carpetaArchivos: 'archivos', frontend: 'front',
    pgBin: 'pg\bin', carpetaCopias: 'datos\copias',
  });
  assert.equal(env.AGRONEXO_PG_BIN, 'pg\bin');
  assert.equal(env.AGRONEXO_COPIAS_DIR, 'datos\copias');
});

test('si la API dejó un aviso, el error que se muestra explica la actualización', () => {
  const carpeta = carpetaTemporal();
  fs.writeFileSync(
    path.join(carpeta, 'actualizacion-fallida.json'),
    JSON.stringify({ motivo: 'migracion', restaurada: true }),
  );
  const { titulo, mensaje } = describirFallo({
    error: new Error('La API se cerró antes de estar lista.'), carpeta, carpetaLogs: 'C:\logs',
  });
  assert.equal(titulo, 'AgroNexo no pudo actualizarse');
  assert.match(mensaje, /como estaban/);
  assert.match(mensaje, /C:\logs/);
  assert.doesNotMatch(mensaje, /La API se cerró/);
});

test('sin aviso, se muestra el error de siempre', () => {
  const { titulo, mensaje } = describirFallo({
    error: new Error('La API se cerró antes de estar lista.'), carpeta: carpetaTemporal(), carpetaLogs: 'C:\logs',
  });
  assert.equal(titulo, 'AgroNexo no pudo iniciar');
  assert.match(mensaje, /La API se cerró antes de estar lista/);
});
