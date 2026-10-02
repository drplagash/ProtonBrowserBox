# ProtonBrowserBox

**Autor: DrPlaga · Licencia MIT**

Firefox ESR en un contenedor, accesible desde tu navegador local y conectado a
Proton VPN a través de Gluetun. Compatible con **OpenVPN TCP/443** y **WireGuard**.
El navegador comparte la red del contenedor VPN y se inicia cuando la VPN pasa
su comprobación de salud.

```text
Tu navegador local -> 127.0.0.1:5800 -> Firefox del contenedor
                                           |
                                    Gluetun / Proton VPN -> Internet
```

La VPN cubre el tráfico del Firefox del contenedor. Las demás aplicaciones y
el navegador del equipo mantienen su conexión habitual. Este es un proyecto
independiente, sin afiliación ni respaldo de Proton AG.

## Requisitos

- Linux con Python 3.11 o superior.
- Docker Engine en ejecución y Docker Compose v2.
- Tu usuario debe poder ejecutar Docker.
- Dispositivo `/dev/net/tun` disponible, también dentro de una máquina virtual.
- Cuenta de Proton VPN y credenciales OpenVPN o un archivo WireGuard `.conf`.
- Espacio adicional para descargar y construir las imágenes Docker.

Linux x86_64 es el objetivo principal. ARM64 depende de la disponibilidad de
las imágenes. Windows y macOS no están validados para esta versión.

El instalador verifica los requisitos; no instala Docker ni modifica la red del
equipo. En una VM, tener acceso web por sí solo no demuestra que el túnel VPN
del contenedor pueda conectarse.

## Descargar e iniciar

```sh
git clone https://github.com/drplagash/ProtonBrowserBox.git
cd ProtonBrowserBox
./setup.sh
```

También podés descargar **Code → Download ZIP**, extraer el proyecto y ejecutar
`sh setup.sh` desde esa carpeta.

El script instala el lanzador, crea las carpetas privadas, permite elegir el
protocolo y los recursos, guarda las credenciales localmente e inicia la VPN y
Firefox. Si ya existe configuración, `./setup.sh` la reutiliza.

Para elegir directamente OpenVPN TCP/443:

```sh
./setup.sh --openvpn-tcp
```

Este modo no requiere descargar un `.conf` ni un `.ovpn`. Es la alternativa
que funcionó durante la prueba manual del proyecto en una VM donde WireGuard
no alcanzaba un estado saludable.

Cuando la terminal muestre `Browser: READY`, abrí:

**[http://127.0.0.1:5800](http://127.0.0.1:5800)**

La página muestra la sesión de Firefox mediante noVNC; si aparece la pantalla
de conexión, seleccioná **Connect**. Navegá dentro de esa sesión de Firefox.
Si elegiste otro puerto, usá la dirección que imprime el lanzador. Las primeras
descargas o la construcción de la imagen pueden tardar varios minutos.

## Encontrar las credenciales de Proton

### OpenVPN TCP/443

1. Abrí [account.protonvpn.com](https://account.protonvpn.com) e iniciá sesión
   con tu cuenta habitual de Proton.
2. Entrá a **Account / Cuenta** en el menú lateral.
3. Buscá **OpenVPN username**. Algunas interfaces muestran la sección como
   **OpenVPN / IKEv2 username** o **Nombre de usuario OpenVPN / IKEv2**.
4. Copiá el **usuario OpenVPN** y la **contraseña OpenVPN** que muestra esa
   sección.
5. Pegalos cuando el script pida `OpenVPN/IKEv2 username` y
   `OpenVPN/IKEv2 password`. La contraseña no se muestra al escribir o pegar.

**Estos datos son distintos del correo y la contraseña de inicio de sesión de
Proton.** Cada persona usa sus propias credenciales.

Ruta directa al panel: [account.protonvpn.com/account](https://account.protonvpn.com/account).
Referencia oficial: [Cómo iniciar sesión y encontrar el usuario OpenVPN](https://protonvpn.com/support/vpn-login).

### WireGuard

1. Iniciá sesión en [account.protonvpn.com](https://account.protonvpn.com).
2. Entrá a **Downloads / Descargas → WireGuard configuration**.
3. Elegí nombre, plataforma y un servidor accesible con tu plan. Seleccioná
   **Create** y después **Download** para obtener el archivo `.conf`.
4. Ejecutá `./setup.sh --wireguard`. Cuando indique la carpeta, copiá allí el
   archivo y presioná Enter para continuar.

La carpeta de importación es:

```text
ProtonBrowserBox/config/vpn/wireguard/
```

Podés copiar el archivo desde el explorador de archivos o desde la terminal:

```sh
cp ~/Downloads/tu-archivo-proton.conf config/vpn/wireguard/
```

No necesitás ejecutar `chmod`: el proyecto ajusta los permisos. Si hay un solo
`.conf`, lo selecciona automáticamente; si hay varios, ofrece una lista.
Si contiene un peer completo, usa el servidor exacto del archivo; si sólo
contiene la clave privada, usa la selección de servidores Free de Gluetun.

Referencia oficial: [Descargar configuraciones WireGuard](https://protonvpn.com/support/wireguard-configurations).

## Recursos y perfil

Los asistentes `config` y `config --openvpn-tcp` permiten elegir:

| Perfil | RAM de Firefox | Presupuesto del perfil en disco |
| --- | --- | --- |
| LIGHT | 1024 MB | 2048 MB |
| NORMAL | 2048 MB | 4096 MB |
| COMFORT | 4096 MB | 8192 MB |
| CUSTOM | Valor elegido | Valor elegido |

- **Persistent:** conserva el perfil, cookies, historial y sesiones entre usos.
- **Ephemeral:** utiliza un perfil temporal que se elimina al ejecutar `stop`.
- **Local web port:** `5800` por defecto. Es el puerto de la pantalla local;
  OpenVPN sigue conectándose por TCP/443.
- **Resolution:** `1920x1080` por defecto; define el escritorio del contenedor.

Gluetun y el escritorio consumen recursos adicionales a los de Firefox. El
presupuesto de disco se comprueba antes de iniciar: no es una cuota Docker ni
incluye las imágenes, capas y logs. No se borran perfiles automáticamente para
recuperar espacio.

## Uso diario y comandos

Ejecutá estos comandos desde la carpeta del proyecto. `./vpn-browser` sin
argumentos equivale a `./vpn-browser start`. Después de `install.sh`, también
podés usar `vpn-browser` si `~/.local/bin` está en tu `PATH`.

| Comando | Función |
| --- | --- |
| `./vpn-browser` o `./vpn-browser start` | Inicia Gluetun, espera la VPN y después inicia Firefox; imprime la URL local. |
| `./vpn-browser stop` | Detiene los contenedores y limpia el perfil efímero, si corresponde. |
| `./vpn-browser status` | Muestra protocolo, recursos, puerto, tamaño del perfil, salud de contenedores y existencia de secretos. |
| `./vpn-browser doctor` | Revisa Docker, Compose, TUN, configuración, permisos, estructura de aislamiento y recursos. No prueba por sí solo que la VPN conecte. |
| `./vpn-browser config` | Configura recursos y vuelve a importar WireGuard desde la carpeta de `.conf`. |
| `./vpn-browser config --openvpn-tcp` | Configura recursos, puerto, perfil y credenciales para OpenVPN TCP/443. |
| `./vpn-browser server` | Menú para seleccionar el modo VPN y el servidor. |
| `./vpn-browser server --openvpn-tcp` | Cambia a OpenVPN TCP/443 y pide sus credenciales. Conserva los recursos existentes; si no hay configuración, usa los valores NORMAL. |
| `./vpn-browser server --auto` | Cambia a WireGuard con selección automática de servidores Proton Free. Requiere una clave WireGuard previamente importada. |
| `./vpn-browser server --country "United States"` | Cambia a WireGuard y limita la selección a un país con servidores Free disponibles en Gluetun. |
| `./vpn-browser server --exact` | Cambia al peer WireGuard exacto previamente importado. Requiere los datos completos del peer. |
| `./vpn-browser logs` | Muestra los últimos 200 registros de los servicios, con redacción de secretos conocidos. |
| `./vpn-browser logs --tail 50` | Limita la cantidad de registros mostrados. |
| `./vpn-browser --debug status` | Activa el nivel de registro de diagnóstico; `--debug` se coloca antes del comando. |
| `./vpn-browser clear-profile` | Solicita `DELETE PROFILE` antes de borrar el perfil persistente. Ejecutá `stop` primero. |
| `./vpn-browser reset` | Solicita `DELETE CONFIG` y elimina ajustes y secretos importados, incluidas las credenciales OpenVPN. Conserva los `.conf` originales y los perfiles. Ejecutá `stop` primero. |
| `./vpn-browser version` | Muestra la versión del lanzador. |
| `./vpn-browser --help` | Lista los comandos y opciones. |
| `./setup.sh` | Instala, configura e inicia; reutiliza una configuración existente. |
| `./setup.sh --openvpn-tcp` | Fuerza una nueva configuración guiada de OpenVPN e inicia. |
| `./setup.sh --wireguard` | Fuerza una nueva importación guiada de WireGuard e inicia. |
| `./install.sh` | Verifica requisitos, crea carpetas e instala el acceso en `~/.local/bin/vpn-browser`; no inicia la VPN. |
| `./uninstall.sh` | Retira el acceso instalado y pregunta si se deben eliminar configuración y datos. Ejecutá `stop` primero. |
| `scripts/network-diagnose.sh` | Prueba HTTPS del host, requisitos, una ruta UDP y la salud real de Gluetun. Al terminar detiene la appliance; puede mostrar IPs y endpoints. |

Los cambios de protocolo, servidor o configuración se aplican al reiniciar:

```sh
./vpn-browser stop
./vpn-browser server --openvpn-tcp
./vpn-browser
```

Para ajustar recursos o puerto manteniendo OpenVPN, usá
`./vpn-browser config --openvpn-tcp` con los contenedores detenidos.
`server --auto`, `--country` y `--exact` seleccionan **WireGuard**, no servidores
OpenVPN. La selección depende de los servidores que Proton y Gluetun ofrezcan
en ese momento; un país válido no garantiza disponibilidad.

## Archivos locales y credenciales

```text
config/vpn/
  settings.json                Ajustes del equipo, sin contraseña
  compose.override.yaml        Configuración Docker generada por el lanzador
  wireguard/                   Tus archivos .conf descargados de Proton
  secrets/
    wireguard_private_key      Clave privada importada de WireGuard
    openvpn_user               Usuario manual de OpenVPN
    openvpn_password           Contraseña manual de OpenVPN
  data/
    browser-profile/           Perfil persistente
    ephemeral-browser-profile/ Perfil temporal
```

El proyecto crea directorios privados y secretos con permisos restringidos.
Los archivos de credenciales se guardan localmente en texto plano, protegidos
por permisos; no están cifrados en disco. `config/vpn/` está excluido de Git.
También se excluyen `.env`, logs y archivos `.conf`, `.ovpn`, `.key` y `.pem`.
No compartas ni publiques tu carpeta de ejecución completa: usá los archivos
versionados o el ZIP limpio del proyecto.

Para instalaciones avanzadas, `VPN_BROWSER_CONFIG_DIR` y
`VPN_BROWSER_DATA_DIR` permiten cambiar las rutas locales. Si usás rutas fuera
del proyecto, aplicá las mismas variables a todos los comandos y no agregues
sus archivos a Git.

## Problemas frecuentes

### La VPN no pasa la comprobación de salud

```sh
./vpn-browser doctor
./vpn-browser logs --tail 120
```

El arranque espera hasta 90 segundos por la VPN y hasta 60 por el navegador.
Una VPN no saludable impide que el lanzador inicie el navegador. Si los logs
indican `AUTH_FAILED`, revisá las credenciales **OpenVPN**, no las de tu correo.
Si WireGuard no conecta, probá OpenVPN TCP/443 o regenerá tu `.conf`.

La aplicación oficial de Proton puede funcionar y el contenedor fallar:
pueden estar usando otro protocolo, servidor o ruta. Para comprobar la
conexión de esta appliance:

```sh
scripts/network-diagnose.sh
```

La prueba de envío UDP sólo confirma que existe una ruta local; no demuestra
que el servidor haya aceptado el paquete ni que WireGuard pueda conectar.
Revisá el diagnóstico y los logs antes de compartirlos: pueden incluir IPs y
otros datos de tu entorno.

### Firefox dice "Unable to connect" o "The connection was reset"

Confirmá `Browser: READY` y revisá `./vpn-browser status`. Usá
`http://127.0.0.1:5800`, o el puerto que imprimió el lanzador. `localhost`
puede resolver a IPv6 mientras la appliance escucha en IPv4. Ejecutar sólo
`config` guarda ajustes; para iniciar hace falta `./vpn-browser`.

### El puerto 6666 está restringido

Firefox bloquea ciertos puertos. Mantené `5800` o elegí otro puerto web
permitido y disponible. No hace falta desactivar la protección de Firefox.

### Permisos, Docker o TUN

`./vpn-browser doctor` indica qué requisito falta. Si Docker no es accesible
para tu usuario o la VM no dispone de `/dev/net/tun`, hay que corregir ese
requisito del host. El proyecto gestiona automáticamente los permisos de sus
archivos de configuración.

## Alcance y estado

Versión inicial en desarrollo. OpenVPN TCP/443 fue probado manualmente durante
el desarrollo. Las pruebas automáticas verifican código y estructura Compose;
no certifican anonimato ni ausencia de fugas en todas las redes.

El firewall de Gluetun y el espacio de red compartido sostienen el kill switch.
La interfaz sólo se publica en `127.0.0.1` y no incorpora autenticación web.
No publiques ese puerto en Internet o en la LAN. El script de prueba automática
de caída del túnel todavía es un marcador pendiente.

## Desarrollo y pruebas

```sh
python3 -m pip install -e '.[dev]'
ruff check .
python3 -m pytest
scripts/smoke-test.sh
scripts/release-check.sh
```

`smoke-test.sh` ejecuta pruebas, valida Compose y construye la imagen.
`release-check.sh` agrega las herramientas de análisis disponibles y declara
los controles omitidos. Las pruebas con Proton real necesitan una configuración:

```sh
VPN_BROWSER_PROTON_CONF=/ruta/privada/proton.conf scripts/integration-test.sh
```

Consulta [instalación](docs/install.md), [diagnóstico](docs/troubleshooting.md),
[arquitectura](docs/architecture.md), [pruebas](docs/testing.md),
[seguridad](docs/security.md) y [contribuciones](CONTRIBUTING.md).
