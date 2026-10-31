const fs = require('node:fs');
const path = require('node:path');
const { app, dialog, Menu } = require('electron');

const {
  HOST, localizarMotor, cargarSecretos, puertoLibre, entornoMotor,
} = require('./src/entorno');
const { Postgres } = require('./src/postgres');
const { lanzar, detener, esperarSalud } = require('./src/procesos');
const {
  bloquearPermisos, restringirNavegacion, crearVentana, pantallaInicial,
} = require('./src/ventana');

const ESPERA_API_MS = 120000;

const estado = { ventana: null, postgres: null, api: null, worker: null, apagando: false };
let archivoLog = null;

function registrar(mensaje) {
  if (!archivoLog) return;
  fs.appendFileSync(archivoLog, `${new Date().toISOString()} ${mensaje}\n`);
}

async function arrancar() {
  Menu.setApplicationMenu(null);
  bloquearPermisos();

  const carpetaDatos = app.getPath('userData');
  const carpetaLogs = path.join(carpetaDatos, 'logs');
  const carpetaArchivos = path.join(carpetaDatos, 'archivos');
  fs.mkdirSync(carpetaLogs, { recursive: true });
  fs.mkdirSync(carpetaArchivos, { recursive: true });
  archivoLog = path.join(carpetaLogs, 'lanzador.log');

  const motor = localizarMotor(app.isPackaged);
  const secretos = cargarSecretos(carpetaDatos);
  const puertoPg = await puertoLibre();
  const puertoApi = await puertoLibre();
  const origen = `http://${HOST}:${puertoApi}`;

  // Tiene que registrarse antes de crear la ventana para cubrirla desde el inicio.
  restringirNavegacion(origen);
  estado.ventana = crearVentana();
  await estado.ventana.loadFile(pantallaInicial);

  estado.postgres = new Postgres({
    pgBin: motor.pgBin, carpetaDatos, secretos, puerto: puertoPg, registrar,
  });
  await estado.postgres.iniciar();
  registrar(`Postgres listo en el puerto ${puertoPg}`);

  const env = entornoMotor({
    secretos, puertoPg, puertoApi, carpetaArchivos, frontend: motor.frontend,
  });
  estado.api = lanzar({
    exe: motor.api,
    env: { ...env, ADMIN_PASSWORD: secretos.adminPassword },
    archivoLog: path.join(carpetaLogs, 'api.log'),
    registrar,
  });
  await esperarSalud(`${origen}/api/v1/health`, { timeoutMs: ESPERA_API_MS, proceso: estado.api });
  registrar(`API lista en ${origen}`);

  // El worker arranca después de la API para no competir con las migraciones.
  estado.worker = lanzar({
    exe: motor.worker, env, archivoLog: path.join(carpetaLogs, 'worker.log'), registrar,
  });

  await estado.ventana.loadURL(origen);
}

async function apagar() {
  if (estado.apagando) return;
  estado.apagando = true;
  const pasos = [
    ['worker', () => detener(estado.worker)],
    ['API', () => detener(estado.api)],
    ['Postgres', () => estado.postgres && estado.postgres.detener()],
  ];
  for (const [nombre, paso] of pasos) {
    try {
      await paso();
    } catch (error) {
      registrar(`No se pudo detener ${nombre}: ${error.message}`);
    }
  }
}

async function fallar(error) {
  registrar(`Error al iniciar: ${error.stack || error.message}`);
  dialog.showErrorBox(
    'AgroNexo no pudo iniciar',
    `${error.message}\n\nLos registros están en:\n${path.dirname(archivoLog || app.getPath('userData'))}`,
  );
  await apagar();
  app.exit(1);
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    const { ventana } = estado;
    if (!ventana) return;
    if (ventana.isMinimized()) ventana.restore();
    ventana.focus();
  });
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', (evento) => {
    if (estado.apagando) return;
    evento.preventDefault();
    apagar().finally(() => app.exit(0));
  });
  app.whenReady().then(arrancar).catch(fallar);
}
