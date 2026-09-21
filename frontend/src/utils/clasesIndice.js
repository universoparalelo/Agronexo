// Nombre visible de cada clase de valor de un índice. Los identificadores
// (critica/deficiente/normal/vigorosa) son los que guarda el worker en el
// GeoJSON y consumen el diagnóstico, los reportes y las exportaciones — no se
// renombran; solo cambia lo que ve el usuario. No confundir con la *severidad*
// del diagnóstico (crítica/moderada/leve), que habla de la gravedad del problema.
export const ETIQUETA_CLASE = {
  critica: 'Muy bajo',
  deficiente: 'Bajo',
  normal: 'Medio',
  vigorosa: 'Alto',
}

export const etiquetaClase = (clase) => ETIQUETA_CLASE[clase] ?? clase
