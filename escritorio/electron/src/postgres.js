const { execFile, spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const { HOST, BASE_DE_DATOS, USUARIO_PG, entornoBase } = require('./entorno');

// Sin shell: los argumentos viajan como lista y nunca se interpretan como comando.
function ejecutar(exe, args, { env = entornoBase(), timeout = 120000 } = {}) {
  return new Promise((resolve, reject) => {
    execFile(exe, args, { env, timeout, windowsHide: true }, (error, stdout, stderr) => {
      if (error) {
        error.message = `${error.message}\n${stderr}`.trim();
        reject(error);
      } else {
        resolve(stdout);
      }
    });
  });
}

// El servidor que deja corriendo `pg_ctl start` hereda los canales de salida: con execFile
// el programa nunca se da por terminado. Se descarta la salida (va al archivo de -l).
function ejecutarSinSalida(exe, args, archivoLog) {
  return new Promise((resolve, reject) => {
    const hijo = spawn(exe, args, { stdio: 'ignore', windowsHide: true, shell: false });
    hijo.once('error', reject);
    hijo.once('exit', (codigo) => {
      if (codigo === 0) resolve();
      else reject(new Error(`${path.basename(exe)} terminó con código ${codigo}. Revisá ${archivoLog}`));
    });
  });
}

class Postgres {
  constructor({ pgBin, carpetaDatos, secretos, puerto, registrar }) {
    this.pgBin = pgBin;
    this.datos = path.join(carpetaDatos, 'pgdata');
    this.log = path.join(carpetaDatos, 'logs', 'postgres.log');
    this.carpetaDatos = carpetaDatos;
    this.secretos = secretos;
    this.puerto = puerto;
    this.registrar = registrar;
  }

  exe(nombre) {
    return path.join(this.pgBin, `${nombre}.exe`);
  }

  async iniciar() {
    if (!fs.existsSync(path.join(this.datos, 'PG_VERSION'))) {
      await this.crearCluster();
    }
    // Si la app anterior se cerró mal puede haber quedado un Postgres vivo.
    if (await this.estaCorriendo()) {
      this.registrar('Postgres ya estaba corriendo: se detiene antes de arrancar');
      await this.detener();
    }
    await ejecutarSinSalida(this.exe('pg_ctl'), [
      'start', '-D', this.datos, '-w', '-t', '60', '-l', this.log,
      '-o', `-p ${this.puerto} -c listen_addresses=${HOST}`,
    ], this.log);
    await this.crearBaseSiFalta();
  }

  async crearCluster() {
    this.registrar('Primer arranque: se crea la base de datos');
    const archivoClave = path.join(this.carpetaDatos, 'pg.pwfile');
    fs.writeFileSync(archivoClave, this.secretos.pgPassword, { mode: 0o600 });
    try {
      // scram-sha-256 en lugar de "trust": aunque otro programa del equipo llegue al
      // puerto, sin la contraseña no entra.
      await ejecutar(this.exe('initdb'), [
        '-D', this.datos, '-U', USUARIO_PG, '--pwfile', archivoClave,
        '--auth=scram-sha-256', '-E', 'UTF8',
      ]);
    } finally {
      fs.rmSync(archivoClave, { force: true });
    }
  }

  async estaCorriendo() {
    try {
      await ejecutar(this.exe('pg_ctl'), ['status', '-D', this.datos]);
      return true;
    } catch (error) {
      // pg_ctl status devuelve 3 cuando el servidor no está corriendo.
      if (error.code === 3) return false;
      throw error;
    }
  }

  async crearBaseSiFalta() {
    const env = { ...entornoBase(), PGPASSWORD: this.secretos.pgPassword };
    const conexion = ['-h', HOST, '-p', String(this.puerto), '-U', USUARIO_PG];
    const existe = await ejecutar(this.exe('psql'), [
      ...conexion, '-d', 'postgres', '-tAc',
      `SELECT 1 FROM pg_database WHERE datname = '${BASE_DE_DATOS}'`,
    ], { env });
    if (existe.trim() !== '1') {
      await ejecutar(this.exe('createdb'), [...conexion, BASE_DE_DATOS], { env });
    }
  }

  async detener() {
    await ejecutar(this.exe('pg_ctl'), ['stop', '-D', this.datos, '-m', 'fast', '-w', '-t', '30']);
  }
}

module.exports = { Postgres };
