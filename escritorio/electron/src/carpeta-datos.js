const fs = require('node:fs');
const path = require('node:path');

// Hasta la v4.0.0 la app se llamaba "AgroNexo (prototipo)" y Electron guarda los datos
// en una carpeta con el nombre de la app: sin esto, quien ya la usaba no vería sus lotes.
const NOMBRE_ANTERIOR = 'AgroNexo (prototipo)';

function tieneDatos(carpeta) {
  return fs.existsSync(path.join(carpeta, 'secretos.json'));
}

// Corre antes de que Electron use la carpeta (el bloqueo de instancia única ya la toca).
// Si no se puede renombrar (por ejemplo, un Postgres de la versión vieja quedó vivo)
// se sigue usando la carpeta vieja: nunca se copia ni se borra nada.
function resolverCarpetaDatos(carpetaNueva) {
  const carpetaVieja = path.join(path.dirname(carpetaNueva), NOMBRE_ANTERIOR);
  if (!tieneDatos(carpetaVieja) || tieneDatos(carpetaNueva)) {
    return { carpeta: carpetaNueva, accion: 'sin-cambios' };
  }
  if (!fs.existsSync(carpetaNueva)) {
    try {
      fs.renameSync(carpetaVieja, carpetaNueva);
      return { carpeta: carpetaNueva, accion: 'renombrada' };
    } catch (error) {
      return { carpeta: carpetaVieja, accion: 'vieja', motivo: error.message };
    }
  }
  return { carpeta: carpetaVieja, accion: 'vieja', motivo: `${carpetaNueva} ya existe` };
}

function describirResolucion({ carpeta, accion, motivo }) {
  if (accion === 'renombrada') return `Carpeta de datos renombrada a ${carpeta}`;
  if (accion === 'vieja') return `Se sigue usando la carpeta de datos ${carpeta} (${motivo})`;
  return null;
}

module.exports = { NOMBRE_ANTERIOR, resolverCarpetaDatos, describirResolucion };
