const fs = require('node:fs');
const path = require('node:path');

const ARCHIVO_AVISO = 'actualizacion-fallida.json';

function carpetaCopias(carpetaDatos) {
  return path.join(carpetaDatos, 'copias');
}

// La API deja este archivo cuando no pudo actualizar la base (app/core/copia_migracion.py).
function leerAviso(carpeta) {
  try {
    return JSON.parse(fs.readFileSync(path.join(carpeta, ARCHIVO_AVISO), 'utf8'));
  } catch {
    return null;
  }
}

function borrarAviso(carpeta) {
  fs.rmSync(path.join(carpeta, ARCHIVO_AVISO), { force: true });
}

function mensajeDelAviso(aviso, carpeta) {
  if (aviso.motivo === 'sin_copia') {
    return 'No se pudo guardar la copia de seguridad que se hace antes de actualizar '
      + '(¿falta espacio en el disco?). No se tocó tu base de datos.\n\n'
      + 'Liberá espacio y volvé a abrir AgroNexo.';
  }
  if (aviso.restaurada) {
    return 'No se pudo actualizar la base de datos a esta versión. '
      + 'Tus datos quedaron como estaban antes de actualizar.\n\n'
      + 'Volvé a instalar la versión anterior de AgroNexo y avisanos de este error.';
  }
  return 'No se pudo actualizar la base de datos y tampoco se pudo restaurar la copia sola.\n\n'
    + `No borres nada: la copia de seguridad está en:\n${carpeta}\n\nAvisanos de este error.`;
}

// Lo que se le muestra a la persona cuando la app no puede iniciar: si la API dejó un aviso de
// que falló la actualización de la base, se explica eso; si no, el error tal cual.
function describirFallo({ error, carpeta, carpetaLogs }) {
  const aviso = leerAviso(carpeta);
  const registros = `Los registros están en:
${carpetaLogs}`;
  if (aviso) {
    return {
      titulo: 'AgroNexo no pudo actualizarse',
      mensaje: `${mensajeDelAviso(aviso, carpeta)}

${registros}`,
    };
  }
  return { titulo: 'AgroNexo no pudo iniciar', mensaje: `${error.message}

${registros}` };
}

module.exports = {
  carpetaCopias, leerAviso, borrarAviso, mensajeDelAviso, describirFallo,
};
