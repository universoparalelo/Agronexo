; D7: al desinstalar se pregunta si se borran también los datos (base y archivos).
; La respuesta por defecto es "No": quien reinstala recupera todo como estaba.
!macro customUnInstall
  ; Silencioso = actualización: el instalador nuevo corre el desinstalador viejo así.
  IfSilent agronexo_fin
  MessageBox MB_YESNO|MB_ICONQUESTION|MB_DEFBUTTON2 "¿Querés borrar también tus datos (lotes, análisis y archivos)?$\r$\n$\r$\nSi elegís No, quedan guardados y se recuperan al volver a instalar AgroNexo." IDNO agronexo_fin
  RMDir /r "$APPDATA\${PRODUCT_FILENAME}"
  ; Carpeta de datos de las versiones que se llamaban "AgroNexo (prototipo)".
  RMDir /r "$APPDATA\AgroNexo (prototipo)"
  agronexo_fin:
!macroend
