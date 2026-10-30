const path = require('node:path');
const { BrowserWindow, app, session } = require('electron');

// La app no necesita ningún permiso del navegador (cámara, micrófono, ubicación...).
function bloquearPermisos() {
  session.defaultSession.setPermissionRequestHandler((_contenido, _permiso, responder) => responder(false));
  session.defaultSession.setPermissionCheckHandler(() => false);
}

// Aplica a toda ventana o pestaña que cree Electron: solo puede mostrar la API local.
function restringirNavegacion(origenPermitido) {
  app.on('web-contents-created', (_evento, contenido) => {
    contenido.on('will-navigate', (evento, url) => {
      if (url !== origenPermitido && !url.startsWith(`${origenPermitido}/`)) evento.preventDefault();
    });
    contenido.setWindowOpenHandler(() => ({ action: 'deny' }));
    contenido.on('will-attach-webview', (evento) => evento.preventDefault());
  });
}

function crearVentana() {
  const ventana = new BrowserWindow({
    width: 1400,
    height: 900,
    show: false,
    backgroundColor: '#ffffff',
    title: 'AgroNexo',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      webviewTag: false,
      spellcheck: false,
    },
  });
  ventana.once('ready-to-show', () => ventana.show());
  return ventana;
}

const pantallaInicial = path.join(__dirname, '..', 'splash.html');

module.exports = { bloquearPermisos, restringirNavegacion, crearVentana, pantallaInicial };
