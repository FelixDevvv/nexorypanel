# NexoryPanel

Panel local de administración de servidores Minecraft Java, pensado para Windows. La interfaz se inspira en los ejemplos compartidos: navegación lateral, superficies oscuras y acentos configurables.

## Ejecutar en desarrollo

1. Instala Python 3.11 o superior y Java para ejecutar servidores.
2. Ejecuta `start.bat`.
3. Abre <http://127.0.0.1:5000>.
4. Se abrirá el navegador. La primera cuenta registrada se convierte en administradora. Guárdala: no hay recuperación de contraseña.

El panel crea `data\` junto a la aplicación. Ahí mantiene la base SQLite, una clave de sesión aleatoria y los archivos de cada servidor. No borres ese directorio si quieres conservar los datos.

## Crear el ejecutable

Ejecuta `build-exe.bat`; el ejecutable se genera en la carpeta raíz del proyecto como `NexoryPanel.exe`, fuera de `dist\`. Incluye el icono de NexoryPanel y conserva la consola para mostrar el registro de depuración. Los datos se guardan en `data\` junto al `.exe`. El mismo icono aparece como favicon de la web.

## Sitio web y descargas

- Sitio público: <https://felixdevvv.github.io/nexorypanel/>
- Código y versiones: <https://github.com/FelixDevvv/nexorypanel>
- Descarga para Windows: <https://github.com/FelixDevvv/nexorypanel/releases/latest/download/NexoryPanel.exe>
- SHA-256 de la versión v0.1.0: `docs\assets\NexoryPanel-v0.1.0.exe.sha256`
- En versiones futuras, el Release incluirá automáticamente su archivo `NexoryPanel.exe.sha256`.

La landing está en `docs\` y se publica con GitHub Pages. Al crear un tag `v*`, GitHub Actions compila el ejecutable para Windows, calcula su suma SHA-256 y adjunta ambos archivos a un Release. La suma permite comprobar que el archivo descargado coincide con el publicado; no acredita quién lo creó ni reemplaza una firma digital.

## Funcionalidad incluida

- Registro/inicio de sesión local, contraseñas con hash y primera cuenta administradora.
- Panel de usuario y administración; asignación de servidores, usuarios, RAM, almacenamiento y puerto.
- Cuotas de asignación por nodo y servidor. Se verifican las operaciones de archivos y el proceso Java se detiene si el almacenamiento administrado excede su cuota. La RAM de Java se limita con `-Xmx`; Windows no ofrece aquí un límite duro de memoria de proceso.
- Tipos Paper, Purpur, Vanilla y Folia. Lista versiones/builds mediante APIs oficiales y descarga el JAR desde dominios oficiales permitidos.
- Al administrar un servidor, navegación contextual para Dashboard, Consola, Archivos, Versiones y Plugins; el selector de software muestra nombres claros y las versiones/builds disponibles.
- Consola local de proceso, estadísticas aproximadas de CPU/RAM y explorador de archivos con búsqueda, renombrado, carpetas, archivos, subida, ZIP y extracción ZIP segura contra rutas fuera del servidor.
- Editor UTF-8 (máximo 2 MiB) con números de línea, resaltado básico para YAML/Properties/JSON, guardado con Ctrl+S y pestaña para el archivo abierto.
- Búsqueda e instalación de plugins de Modrinth para Paper/Purpur/Folia.
- Generador de plantilla Maven para plugins Bukkit/Paper con `plugin.yml`, clase Java principal y archivo `pom.xml`.
- Tema del panel configurable (paletas, color personalizado y estilos de botones Gradient/Solid/Outline/Glass), junto con Enable Register, límites y nombre del nodo.
- API key opcional para `GET /api/dashboard`; las claves solo se muestran una vez y se almacenan como hash.
- Administración por servidor: Settings, Actividad, Base de datos MySQL, Backups, Network, Schedules, Users colaboradores y Startup.
- Panel de administración global para anuncios, enlaces personalizados, icono, tema, gradiente y estilo Glassed.
- Network administra puertos mediante reglas explícitas de Windows Firewall. La creación de reglas puede requerir permisos de administrador y exponerá los puertos en los perfiles seleccionados.
- MySQL se ofrece como instalación guiada con winget. Las operaciones de base de datos solicitan las credenciales de administrador MySQL; las contraseñas nuevas se muestran una sola vez y solo se conserva su hash.
- Los backups solo se crean con el servidor apagado. Los schedules se ejecutan mientras NexoryPanel está en marcha; los colaboradores deben ser cuentas ya registradas.

## Fuentes de software consultadas

- Purpur expone su API y OpenAPI en <https://api.purpurmc.org/openapi>. El panel consulta `/v2/purpur`, `/v2/purpur/{version}` y descarga `/v2/purpur/{version}/{build}/download`.
- PaperMC publica Paper y Folia en <https://papermc.io/downloads> y Folia en <https://papermc.io/downloads/folia>. El panel usa los endpoints v3 de `https://fill.papermc.io/v3/projects/{paper|folia}/versions` y sus endpoints de builds/descargas.
- El manifiesto de versiones Vanilla es <https://piston-meta.mojang.com/mc/game/version_manifest_v2.json>; el JAR se obtiene del campo `downloads.server.url` de los metadatos de esa versión.
- El marketplace se obtiene de la API de Modrinth: <https://docs.modrinth.com/api/operations/searchProjects/> y <https://docs.modrinth.com/api/operations/getProjectVersions/>.

Las versiones y builds son dinámicas; el panel las consulta a la fuente al crear o instalar una instancia, no las fija en el código.

## Pruebas

Ejecuta `python -m unittest discover -s tests -v` para probar registro/roles, cuotas, aislamiento de rutas, el endpoint de dashboard, los módulos de servidor, Firewall simulado, branding y la plantilla de plugin.

## Límites importantes

Este MVP es un panel local de un solo nodo. Por seguridad solo escucha en `127.0.0.1`; no lo expongas directamente a Internet ni cambies el host sin añadir TLS, protección de acceso, hardening del servidor y una estrategia de copias de seguridad. Todavía no incluye 2FA, recuperación de contraseñas, nodos remotos ni un límite de disco duro a nivel de Windows/NTFS. Los schedules no se ejecutan si NexoryPanel está cerrado y no se implementa restauración de backups. El generador de plugins crea el esqueleto Maven; compilarlo requiere Java/Maven. El editor de archivos permite actualizar manualmente `eula.txt` a `eula=true` después de aceptar el EULA de Minecraft.

## Configuración

- `NEXORY_PORT`: puerto HTTP local (por defecto `5000`).
- `NEXORY_DATA_DIR`: directorio de datos alternativo.
- Si no está compilado, Flask registra errores en la terminal de `start.bat`.
