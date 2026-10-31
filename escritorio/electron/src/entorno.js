const crypto = require('node:crypto');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');

// Todo escucha solo en loopback: ningún servicio queda visible en la red.
const HOST = '127.0.0.1';
const BASE_DE_DATOS = 'agronexo';
const USUARIO_PG = 'agronexo';

function localizarMotor() {
  const base = process.env.AGRONEXO_PROTOTIPO_DIR
    || path.resolve(__dirname, '..', '..', '..', '..', 'trabajo-escritorio');
  const motor = {
    pgBin: path.join(base, 'pg', 'pgsql', 'bin'),
    api: path.join(base, 'motor2', 'dist', 'agronexo-api', 'agronexo-api.exe'),
    frontend: path.join(base, 'motor2', 'dist', 'agronexo-api', 'frontend'),
    worker: path.join(base, 'motor2', 'dist', 'agronexo-worker', 'agronexo-worker.exe'),
  };
  const faltan = Object.values(motor).filter((ruta) => !fs.existsSync(ruta));
  if (faltan.length) {
    throw new Error(`No se encontró el motor empaquetado. Faltan:\n${faltan.join('\n')}`);
  }
  return motor;
}

function cargarSecretos(carpetaDatos) {
  const archivo = path.join(carpetaDatos, 'secretos.json');
  if (fs.existsSync(archivo)) {
    return JSON.parse(fs.readFileSync(archivo, 'utf8'));
  }
  const secretos = {
    pgPassword: crypto.randomBytes(24).toString('hex'),
    jwtSecret: crypto.randomBytes(32).toString('hex'),
    adminPassword: crypto.randomBytes(12).toString('base64url'),
  };
  // flag "wx": nunca pisa un archivo existente; el modo 0o600 no aplica en Windows,
  // donde la protección es la carpeta del usuario en %APPDATA%.
  fs.writeFileSync(archivo, JSON.stringify(secretos), { mode: 0o600, flag: 'wx' });
  return secretos;
}

function puertoLibre() {
  return new Promise((resolve, reject) => {
    const servidor = net.createServer();
    servidor.once('error', reject);
    servidor.listen(0, HOST, () => {
      const { port } = servidor.address();
      servidor.close(() => resolve(port));
    });
  });
}

// Se arranca desde la lista de variables del proceso quitando las que podrían pisar
// la configuración del motor (por ejemplo, las de una terminal de desarrollo con Docker).
const PREFIJOS_EXCLUIDOS = /^(POSTGRES|PG|MINIO|CELERY|JWT|ADMIN|STORAGE|PYTHON|AGRONEXO|REDIS|FRONTEND|ALLOWED|APP_|ELECTRON)/i;

function entornoBase() {
  return Object.fromEntries(
    Object.entries(process.env).filter(([nombre]) => !PREFIJOS_EXCLUIDOS.test(nombre)),
  );
}

function entornoMotor({ secretos, puertoPg, puertoApi, carpetaArchivos, frontend }) {
  const credenciales = `${USUARIO_PG}:${secretos.pgPassword}@${HOST}:${puertoPg}/${BASE_DE_DATOS}`;
  return {
    ...entornoBase(),
    APP_ENV: 'production',
    APP_DEBUG: 'false',
    ALLOWED_ORIGINS: `http://${HOST}:${puertoApi}`,
    POSTGRES_HOST: HOST,
    POSTGRES_PORT: String(puertoPg),
    POSTGRES_DB: BASE_DE_DATOS,
    POSTGRES_USER: USUARIO_PG,
    POSTGRES_PASSWORD: secretos.pgPassword,
    CELERY_BROKER_URL: `sqla+postgresql+psycopg2://${credenciales}`,
    CELERY_RESULT_BACKEND: `db+postgresql+psycopg2://${credenciales}`,
    JWT_SECRET_KEY: secretos.jwtSecret,
    STORAGE_BACKEND: 'disk',
    STORAGE_PATH: carpetaArchivos,
    FRONTEND_DIR: frontend,
    AGRONEXO_HOST: HOST,
    AGRONEXO_PORT: String(puertoApi),
  };
}

module.exports = {
  HOST, BASE_DE_DATOS, USUARIO_PG,
  localizarMotor, cargarSecretos, puertoLibre, entornoBase, entornoMotor,
};
