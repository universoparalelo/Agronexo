; D7: al desinstalar se pregunta si se borran también los datos (base y archivos).
; La respuesta por defecto es "No": quien reinstala recupera todo como estaba.
!macro customUnInstall
  IfSilent +4
  MessageBox MB_YESNO|MB_ICONQUESTION|MB_DEFBUTTON2 "¿Querés borrar también tus datos (lotes, análisis y archivos)?$\r$\n$\r$\nSi elegís No, quedan guardados y se recuperan al volver a instalar AgroNexo." IDNO +2
  RMDir /r "$APPDATA\${PRODUCT_FILENAME}"
!macroend
