const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');

const { Actualizaciones, tamanoDescarga } = require('../src/actualizaciones');

class UpdaterFalso extends EventEmitter {
  constructor({ falloBusqueda = null, falloDescarga = null } = {}) {
    super();
    this.falloBusqueda = falloBusqueda;
    this.falloDescarga = falloDescarga;
    this.descargas = 0;
    this.instalaciones = [];
  }

  async checkForUpdates() {
    if (this.falloBusqueda) {
      this.emit('error', this.falloBusqueda);
      throw this.falloBusqueda;
    }
  }

  async downloadUpdate() {
    this.descargas += 1;
    if (this.falloDescarga) {
      this.emit('error', this.falloDescarga);
      throw this.falloDescarga;
    }
  }

  quitAndInstall(silencioso, reabrir) {
    this.instalaciones.push({ silencioso, reabrir });
  }
}

function armar({ respuestas = [], updater = new UpdaterFalso() } = {}) {
  const dialogos = [];
  const progreso = [];
  const log = [];
  let apagados = 0;
  const marcas = [];
  const ventana = {
    isDestroyed: () => false,
    setProgressBar: (valor) => progreso.push(valor),
  };
  const dialog = {
    showMessageBox: async (_ventana, opciones) => {
      dialogos.push(opciones);
      return { response: respuestas.shift() ?? opciones.cancelId ?? 0 };
    },
  };
  const actualizaciones = new Actualizaciones({
    updater,
    dialog,
    ventana: () => ventana,
    apagar: async () => { apagados += 1; },
    marcarInstalacion: (version) => marcas.push(version),
    versionActual: '4.0.0',
    registrar: (m) => log.push(m),
  });
  actualizaciones.iniciar({ demoraMs: 60000 });
  actualizaciones.detener();
  return {
    actualizaciones, updater, dialogos, progreso, log, marcas, apagados: () => apagados,
  };
}

const infoNueva = { version: '4.1.0', files: [{ size: 450 * 1024 * 1024 }] };

test('no descarga sola ni instala sola al salir', () => {
  const { updater } = armar();
  assert.equal(updater.autoDownload, false);
  assert.equal(updater.autoInstallOnAppQuit, false);
});

test('calcula el tamaño de la descarga en MB', () => {
  assert.equal(tamanoDescarga(infoNueva), 450);
  assert.equal(tamanoDescarga({ version: '4.1.0' }), null);
});

test('pregunta antes de descargar y muestra versión y tamaño', async () => {
  const { actualizaciones, updater, dialogos } = armar({ respuestas: [0] });
  await actualizaciones.ofrecerDescarga(infoNueva);
  assert.equal(updater.descargas, 1);
  assert.match(dialogos[0].message, /4\.1\.0/);
  assert.match(dialogos[0].detail, /4\.0\.0/);
  assert.match(dialogos[0].detail, /450 MB/);
});

test('"Más tarde" no descarga', async () => {
  const { actualizaciones, updater } = armar({ respuestas: [1] });
  await actualizaciones.ofrecerDescarga(infoNueva);
  assert.equal(updater.descargas, 0);
});

test('sin internet la búsqueda falla en silencio', async () => {
  const updater = new UpdaterFalso({ falloBusqueda: new Error('net::ERR_INTERNET_DISCONNECTED') });
  const { actualizaciones, dialogos, log } = armar({ updater });
  await actualizaciones.buscar();
  assert.equal(dialogos.length, 0);
  assert.ok(log.some((m) => m.includes('ERR_INTERNET_DISCONNECTED')));
});

test('si falla la descarga avisa una sola vez y limpia la barra de progreso', async () => {
  const updater = new UpdaterFalso({ falloDescarga: new Error('se cortó') });
  const { actualizaciones, dialogos, progreso } = armar({ updater, respuestas: [0] });
  await actualizaciones.ofrecerDescarga(infoNueva);
  await new Promise((r) => setImmediate(r));
  assert.equal(dialogos.length, 2);
  assert.match(dialogos[1].title, /No se pudo descargar/);
  assert.deepEqual(progreso, [-1]);
});

test('el progreso de la descarga va a la barra de la ventana', () => {
  const { updater, progreso } = armar();
  updater.emit('download-progress', { percent: 42 });
  assert.deepEqual(progreso, [0.42]);
});

test('"Reiniciar e instalar ahora" apaga el motor, marca la instalación y reabre la app', async () => {
  const {
    actualizaciones, updater, apagados, marcas,
  } = armar({ respuestas: [0] });
  await actualizaciones.ofrecerInstalacion({ version: '4.1.0' });
  assert.equal(apagados(), 1);
  assert.deepEqual(marcas, ['4.1.0']);
  assert.deepEqual(updater.instalaciones, [{ silencioso: true, reabrir: true }]);
});

test('"Instalar al cerrar" instala al salir, marca la instalación y también reabre la app', async () => {
  const {
    actualizaciones, updater, apagados, marcas,
  } = armar({ respuestas: [1] });
  await actualizaciones.ofrecerInstalacion({ version: '4.1.0' });
  assert.equal(updater.instalaciones.length, 0);
  assert.deepEqual(marcas, []);
  assert.equal(actualizaciones.instalarSiQuedoPendiente(), true);
  assert.deepEqual(marcas, ['4.1.0']);
  assert.deepEqual(updater.instalaciones, [{ silencioso: true, reabrir: true }]);
  assert.equal(apagados(), 0);
});

test('sin actualización descargada, salir no instala nada', () => {
  const { actualizaciones, updater } = armar();
  assert.equal(actualizaciones.instalarSiQuedoPendiente(), false);
  assert.equal(updater.instalaciones.length, 0);
});
