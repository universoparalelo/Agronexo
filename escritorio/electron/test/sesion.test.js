const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');

const {
  iniciarSesion, scriptInyeccion, esDelOrigen, SesionAutomatica, MAX_REINTENTOS_LOGIN,
} = require('../src/sesion');

function servidorFalso({ loginOk = true } = {}) {
  const pedidos = [];
  const servidor = http.createServer((req, res) => {
    let cuerpo = '';
    req.on('data', (trozo) => { cuerpo += trozo; });
    req.on('end', () => {
      pedidos.push({ url: req.url, auth: req.headers.authorization, cuerpo });
      res.setHeader('Content-Type', 'application/json');
      if (req.url === '/api/v1/auth/login') {
        res.statusCode = loginOk ? 200 : 401;
        res.end(JSON.stringify(loginOk ? { access_token: 'acc', refresh_token: 'ref' } : { detail: 'x' }));
      } else if (req.url === '/api/v1/auth/me') {
        res.end(JSON.stringify({ email: 'a@b.c', nombre: 'Admin "x"' }));
      } else {
        res.statusCode = 404;
        res.end('{}');
      }
    });
  });
  return new Promise((resolve) => {
    servidor.listen(0, '127.0.0.1', () => resolve({
      origen: `http://127.0.0.1:${servidor.address().port}`,
      pedidos,
      cerrar: () => new Promise((r) => servidor.close(r)),
    }));
  });
}

function contenidoFalso(url) {
  const llamadas = { scripts: [], cargas: [] };
  return {
    llamadas,
    getURL: () => url,
    executeJavaScript: async (s) => { llamadas.scripts.push(s); },
    loadURL: async (u) => { llamadas.cargas.push(u); },
  };
}

test('iniciarSesion devuelve tokens y usuario', async () => {
  const srv = await servidorFalso();
  const datos = await iniciarSesion(srv.origen, 'a@b.c', 'clave');
  await srv.cerrar();
  assert.equal(datos.accessToken, 'acc');
  assert.equal(datos.refreshToken, 'ref');
  assert.equal(datos.usuario.email, 'a@b.c');
  assert.deepEqual(JSON.parse(srv.pedidos[0].cuerpo), { email: 'a@b.c', password: 'clave' });
  assert.equal(srv.pedidos[1].auth, 'Bearer acc');
});

test('iniciarSesion falla sin filtrar la contraseña ni los tokens', async () => {
  const srv = await servidorFalso({ loginOk: false });
  await assert.rejects(iniciarSesion(srv.origen, 'a@b.c', 'clave-secreta'), (e) => {
    assert.match(e.message, /401/);
    assert.ok(!e.message.includes('clave-secreta'));
    return true;
  });
  await srv.cerrar();
});

test('scriptInyeccion escapa valores con comillas y saltos de línea', () => {
  const script = scriptInyeccion({
    accessToken: "a'b", refreshToken: 'r\nx', usuario: { nombre: 'Ana "la" \'jefa\'' },
  });
  const guardado = {};
  // eslint-disable-next-line no-new-func
  new Function('localStorage', script)({ setItem: (k, v) => { guardado[k] = v; } });
  assert.equal(guardado.access_token, "a'b");
  assert.equal(guardado.refresh_token, 'r\nx');
  assert.deepEqual(JSON.parse(guardado.usuario), { nombre: 'Ana "la" \'jefa\'' });
});

test('esDelOrigen no acepta dominios que solo empiezan igual', () => {
  const origen = 'http://127.0.0.1:5000';
  assert.ok(esDelOrigen(origen, origen));
  assert.ok(esDelOrigen(`${origen}/login`, origen));
  assert.ok(!esDelOrigen('http://127.0.0.1:50001/', origen));
  assert.ok(!esDelOrigen('http://127.0.0.1:5000.evil.com/', origen));
});

test('alCargar inyecta la sesión y no recarga fuera del login', async () => {
  const srv = await servidorFalso();
  const sesion = new SesionAutomatica({ origen: srv.origen, email: 'a@b.c', password: 'p' });
  const contenido = contenidoFalso(`${srv.origen}/`);
  await sesion.alCargar(contenido);
  await srv.cerrar();
  assert.equal(contenido.llamadas.scripts.length, 1);
  assert.equal(contenido.llamadas.cargas.length, 0);
});

test('alCargar en /login inyecta y vuelve a la raíz, con tope de reintentos', async () => {
  const srv = await servidorFalso();
  const sesion = new SesionAutomatica({ origen: srv.origen, email: 'a@b.c', password: 'p' });
  const contenido = contenidoFalso(`${srv.origen}/login`);
  for (let i = 0; i < MAX_REINTENTOS_LOGIN + 2; i += 1) await sesion.alCargar(contenido);
  await srv.cerrar();
  assert.equal(contenido.llamadas.cargas.length, MAX_REINTENTOS_LOGIN);
  assert.ok(contenido.llamadas.cargas.every((u) => u === srv.origen));
});

test('alCargar no escribe en una página de otro origen', async () => {
  const srv = await servidorFalso();
  const sesion = new SesionAutomatica({ origen: srv.origen, email: 'a@b.c', password: 'p' });
  const contenido = contenidoFalso('https://ejemplo.com/');
  await sesion.alCargar(contenido);
  await srv.cerrar();
  assert.equal(contenido.llamadas.scripts.length, 0);
});

test('alCargar registra el error si el login falla y no lo propaga', async () => {
  const srv = await servidorFalso({ loginOk: false });
  const registros = [];
  const sesion = new SesionAutomatica({
    origen: srv.origen, email: 'a@b.c', password: 'p', registrar: (m) => registros.push(m),
  });
  await sesion.alCargar(contenidoFalso(`${srv.origen}/login`));
  await srv.cerrar();
  assert.equal(registros.length, 1);
  assert.match(registros[0], /401/);
});
