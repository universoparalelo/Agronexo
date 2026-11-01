// El usuario no escribe contraseña: el lanzador inicia sesión con la cuenta local y deja
// los tokens en el localStorage de la ventana, igual que lo haría la pantalla de login.

const RENOVACION_MS = 20 * 60 * 1000; // el access token dura 30 minutos
const MAX_REINTENTOS_LOGIN = 3;

async function iniciarSesion(origen, email, password, fetchFn = fetch) {
  const api = `${origen}/api/v1`;
  const respuestaLogin = await fetchFn(`${api}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!respuestaLogin.ok) throw new Error(`El inicio de sesión automático falló (HTTP ${respuestaLogin.status})`);
  const tokens = await respuestaLogin.json();

  const respuestaYo = await fetchFn(`${api}/auth/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  if (!respuestaYo.ok) throw new Error(`No se pudo leer el usuario (HTTP ${respuestaYo.status})`);
  const usuario = await respuestaYo.json();

  return { accessToken: tokens.access_token, refreshToken: tokens.refresh_token, usuario };
}

// JSON.stringify deja cada valor como literal JS escapado: ningún dato rompe el script.
function scriptInyeccion({ accessToken, refreshToken, usuario }) {
  return [
    `localStorage.setItem('access_token', ${JSON.stringify(accessToken)});`,
    `localStorage.setItem('refresh_token', ${JSON.stringify(refreshToken)});`,
    `localStorage.setItem('usuario', ${JSON.stringify(JSON.stringify(usuario))});`,
  ].join('\n');
}

function esDelOrigen(url, origen) {
  return url === origen || url.startsWith(`${origen}/`);
}

class SesionAutomatica {
  constructor({
    origen, email, password, registrar = () => {}, fetchFn = fetch, renovacionMs = RENOVACION_MS,
  }) {
    this.origen = origen;
    this.email = email;
    this.password = password;
    this.registrar = registrar;
    this.fetchFn = fetchFn;
    this.renovacionMs = renovacionMs;
    this.datos = null;
    this.reintentosLogin = 0;
    this.temporizador = null;
  }

  async renovar() {
    this.datos = await iniciarSesion(this.origen, this.email, this.password, this.fetchFn);
  }

  // Solo escribe en páginas de la API local; nunca en otra URL que llegue a la ventana.
  async inyectar(contenido) {
    if (!this.datos || !esDelOrigen(contenido.getURL(), this.origen)) return false;
    await contenido.executeJavaScript(scriptInyeccion(this.datos));
    return true;
  }

  async alCargar(contenido) {
    try {
      if (!this.datos) await this.renovar();
      if (!(await this.inyectar(contenido))) return;
      const { pathname } = new URL(contenido.getURL());
      if (pathname !== '/login') {
        this.reintentosLogin = 0;
        return;
      }
      if (this.reintentosLogin >= MAX_REINTENTOS_LOGIN) {
        this.registrar('La app sigue mostrando el login después de iniciar sesión; se deja de insistir');
        return;
      }
      this.reintentosLogin += 1;
      await contenido.loadURL(this.origen);
    } catch (error) {
      this.registrar(`Sesión automática: ${error.message}`);
    }
  }

  adjuntar(ventana) {
    const contenido = ventana.webContents;
    const alCambiar = () => this.alCargar(contenido);
    contenido.on('did-finish-load', alCambiar);
    contenido.on('did-navigate-in-page', alCambiar);

    this.temporizador = setInterval(async () => {
      try {
        await this.renovar();
        await this.inyectar(contenido);
      } catch (error) {
        this.registrar(`No se pudo renovar la sesión: ${error.message}`);
      }
    }, this.renovacionMs);
    this.temporizador.unref();
  }

  detener() {
    clearInterval(this.temporizador);
    this.temporizador = null;
  }
}

module.exports = {
  RENOVACION_MS, MAX_REINTENTOS_LOGIN, iniciarSesion, scriptInyeccion, esDelOrigen, SesionAutomatica,
};
