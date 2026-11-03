# Google Drive para Kodi Jarvis (16.1)

Adaptación comunitaria del addon Google Drive de cguZZman para seguir usando
su flujo de inicio de sesión con un servicio OAuth alojado en Replit. Se
conserva la rama compatible con Kodi/Python 2, el módulo común 1.3.9 y las
declaraciones originales de compatibilidad probadas por el usuario.

No es un producto oficial de Google ni está respaldado por el autor original.
Se mantienen la atribución y las licencias GPL del código upstream.

## Preparar el servicio OAuth

1. Publica el servicio Replit como una aplicación web pública y permanente.
   El servicio mantiene los PIN de inicio de sesión en memoria; por ello se
   configura para una única instancia de VM.
2. Conserva `PROVIDER_GOOGLEDRIVE_CLIENT_ID` y
   `PROVIDER_GOOGLEDRIVE_CLIENT_SECRET` en Secrets de Replit. No los añadas a
   este repositorio ni a un archivo JSON publicado.
3. En Google Cloud, habilita Google Drive API y usa un cliente OAuth de tipo
   **Web application**.
4. Añade como URI de redirección autorizada:
   `https://TU-DOMINIO-PUBLICADO/api/callback`
   Usa el dominio real que Replit muestra después de publicar.

El ámbito solicitado es `https://www.googleapis.com/auth/drive.readonly`.
El servicio no conserva tokens en una base de datos: los mantiene en memoria
solo hasta entregarlos a Kodi.

## Configurar Kodi

En Google Drive → **Settings** → **Advanced** → **Sign-in Server**, introduce:

`https://TU-DOMINIO-PUBLICADO/api`

No incluyas una barra final. Después inicia el alta de cuenta en Kodi y abre
el enlace o QR que muestra el addon desde un navegador en la misma conexión
a Internet que la Raspberry Pi.

## Instalar

El directorio `repository/` contiene el instalador de repositorio de Kodi y los
paquetes de Google Drive y `script.module.clouddrive.common`. Instala
`repository.kodi-drive-1.0.0.zip` desde **Add-ons → Install from zip file**.
Después instala Google Drive desde el repositorio.

Para regenerar el repositorio después de publicar los archivos, ejecuta:

```sh
python3 tools/build_kodi_repository.py \
  --base-url "https://raw.githubusercontent.com/mediacenterpucela-lang/kodi-google-drive-replit/main/repository/"
```

El paquete Kodi es Python 2; el script de empaquetado usa Python 3 y no ejecuta
el addon. Revisa `SOURCE-INFO.md` para las fuentes, revisiones y licencias.

Instalador directo:
https://raw.githubusercontent.com/mediacenterpucela-lang/kodi-google-drive-replit/main/repository/repository.kodi-drive-1.0.0.zip

## Google OAuth en modo de prueba

Si la pantalla de consentimiento de Google está en modo **Testing**, Google
puede limitar los usuarios de prueba y caducar los tokens de renovación.
Añade las cuentas de prueba permitidas y sigue las condiciones de Google antes
de usar el servicio con más usuarios.
