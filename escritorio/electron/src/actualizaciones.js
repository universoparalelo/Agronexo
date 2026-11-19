// Busca versiones nuevas en GitHub Releases. Sin internet (D8) la búsqueda falla en
// silencio y la app sigue igual; se vuelve a intentar en el próximo arranque.
const DEMORA_BUSQUEDA_MS = 15000;

function megas(bytes) {
  return Math.round(bytes / (1024 * 1024));
}

function tamanoDescarga(info) {
  const total = (info.files || []).reduce((suma, archivo) => suma + (archivo.size || 0), 0);
  return total > 0 ? megas(total) : null;
}

class Actualizaciones {
  constructor({
    updater, dialog, ventana, apagar, marcarInstalacion, versionActual, registrar,
  }) {
    this.updater = updater;
    this.dialog = dialog;
    this.ventana = ventana;
    this.apagar = apagar;
    this.marcarInstalacion = marcarInstalacion;
    this.versionActual = versionActual;
    this.registrar = registrar;
    this.descargando = false;
    this.pendiente = null;
  }

  iniciar({ demoraMs = DEMORA_BUSQUEDA_MS } = {}) {
    const { updater } = this;
    // Pesa ~430 MB: se pregunta antes de descargar (puede haber solo datos móviles en el campo).
    updater.autoDownload = false;
    // La instalación al salir la maneja el lanzador, después de cerrar Postgres, la API y el
    // worker: con ellos vivos el instalador no puede reemplazar sus archivos.
    updater.autoInstallOnAppQuit = false;
    updater.logger = {
      info: (m) => this.registrar(`[actualizaciones] ${m}`),
      warn: (m) => this.registrar(`[actualizaciones] ${m}`),
      error: (m) => this.registrar(`[actualizaciones] ${m}`),
      debug: () => {},
    };
    updater.on('update-available', (info) => this.ofrecerDescarga(info));
    updater.on('download-progress', (p) => this.mostrarProgreso(p.percent / 100));
    updater.on('update-downloaded', (info) => this.ofrecerInstalacion(info));
    updater.on('error', (error) => this.alFallar(error));
    this.temporizador = setTimeout(() => this.buscar(), demoraMs);
  }

  detener() {
    clearTimeout(this.temporizador);
  }

  async buscar() {
    try {
      await this.updater.checkForUpdates();
    } catch (error) {
      this.registrar(`No se pudo buscar actualizaciones: ${error.message}`);
    }
  }

  async preguntar(opciones) {
    const ventana = this.ventana();
    const { response } = ventana
      ? await this.dialog.showMessageBox(ventana, opciones)
      : await this.dialog.showMessageBox(opciones);
    return response;
  }

  mostrarProgreso(fraccion) {
    const ventana = this.ventana();
    if (ventana && !ventana.isDestroyed()) ventana.setProgressBar(fraccion);
  }

  async ofrecerDescarga(info) {
    const tamano = tamanoDescarga(info);
    const respuesta = await this.preguntar({
      type: 'info',
      title: 'Actualización disponible',
      message: `Hay una versión nueva de AgroNexo: ${info.version}`,
      detail: `Tenés la ${this.versionActual}.`
        + `${tamano ? ` La descarga pesa unos ${tamano} MB.` : ''}`
        + ' Mientras se descarga podés seguir usando la app. Tus datos no se tocan.',
      buttons: ['Descargar', 'Más tarde'],
      defaultId: 0,
      cancelId: 1,
    });
    if (respuesta !== 0) {
      this.registrar(`Actualización ${info.version} pospuesta`);
      return;
    }
    this.descargando = true;
    try {
      await this.updater.downloadUpdate();
    } catch (error) {
      // El detalle lo informa alFallar, que recibe el mismo error por el evento.
      this.registrar(`Falló la descarga de ${info.version}: ${error.message}`);
    }
  }

  async ofrecerInstalacion(info) {
    this.descargando = false;
    this.mostrarProgreso(-1);
    this.pendiente = info.version;
    const respuesta = await this.preguntar({
      type: 'info',
      title: 'Actualización lista',
      message: `La versión ${info.version} está lista para instalarse.`,
      detail: 'Para instalarla AgroNexo se cierra y vuelve a abrirse solo en uno o dos minutos'
        + ' (si elegís instalar al cerrar, pasa cuando cierres la app). Mientras tanto no hace'
        + ' falta abrirla. Antes de actualizar la base se guarda una copia.',
      buttons: ['Reiniciar e instalar ahora', 'Instalar al cerrar la app'],
      defaultId: 0,
      cancelId: 1,
    });
    if (respuesta === 0) await this.instalarAhora();
  }

  async instalarAhora() {
    this.registrar(`Se instala la versión ${this.pendiente} y se reabre la app`);
    await this.apagar();
    this.instalar();
  }

  // Lo llama el lanzador al salir, con todo ya detenido. Devuelve true si el instalador
  // se encarga de cerrar la app.
  instalarSiQuedoPendiente() {
    if (!this.pendiente) return false;
    this.registrar(`Se instala la versión ${this.pendiente} al cerrar`);
    this.instalar();
    return true;
  }

  // El instalador corre en silencio, así que siempre reabre la app al terminar: si no, quien
  // la abre a mano antes de que termine la encuentra a medio instalar.
  instalar() {
    this.marcarInstalacion(this.pendiente);
    this.updater.quitAndInstall(true, true);
  }

  async alFallar(error) {
    this.registrar(`Error de actualización: ${error.message}`);
    if (!this.descargando) return;
    this.descargando = false;
    this.mostrarProgreso(-1);
    await this.preguntar({
      type: 'warning',
      title: 'No se pudo descargar la actualización',
      message: 'No se pudo descargar la versión nueva.',
      detail: 'Revisá la conexión a internet. Se vuelve a ofrecer la próxima vez que abras AgroNexo.',
      buttons: ['Aceptar'],
    });
  }
}

module.exports = { Actualizaciones, tamanoDescarga };
