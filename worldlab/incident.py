"""Synthetic incident fixtures and account-scoped observations. No action policy."""
import random
from .observations import agent_view

BRANCHES = ('generic', 'diagnostic')
BRANCH_LABELS = {'generic': 'Estado público genérico', 'diagnostic': 'Diagnóstico técnico consultable'}
INITIAL_POST = ('¿A alguien más le desaparecieron carpetas en Nube Norte? Desde esta mañana no veo varios '
                'archivos. Me preocupa que se hayan perdido datos. ¿Qué está pasando?')
TRUTH = {'permanent_loss': False, 'cause': 'Desfase temporal del índice de sincronización',
         'basis': 'Fixture sintético: todos los objetos siguen en almacenamiento; el índice omite algunas carpetas.'}
ROLES = [
 ('Cliente · estudio de diseño', 'Necesitas entregar un proyecto esta tarde y coordinarte con tus colaboradores.', 'Tu carpeta de entrega no aparece en la aplicación, aunque conservas una copia local.'),
 ('Cliente · comercio', 'Gestionas pedidos y quieres mantener informado a tu equipo sobre el acceso a documentos.', 'Dos carpetas de facturas no aparecen en la aplicación.'),
 ('Cliente · consultoría', 'Debes decidir cómo seguir trabajando con documentos compartidos de tus clientes.', 'Tus archivos se ven normalmente en la web; un colega dice que no encuentra una carpeta.'),
 ('Cliente · fotografía', 'Tienes una entrega pendiente y quieres entender qué opciones tienes para acceder a tus archivos.', 'La aplicación muestra una carpeta vacía. No has comprobado la web.'),
 ('Cliente · comunidad', 'Organizas una comunidad de usuarios y recibes consultas sobre problemas del servicio.', 'Varias personas de tu comunidad preguntan por carpetas que no ven.'),
 ('Cliente · contabilidad', 'Trabajas con información de clientes y debes coordinar la jornada de tu oficina.', 'La sincronización de tu equipo aparece retrasada desde las 09:00.'),
 ('Cliente · educación', 'Compartes materiales de clase y necesitas organizar el trabajo con otros profesores.', 'Un enlace compartido sigue abriendo correctamente un archivo.'),
 ('Cliente · desarrollo', 'Mantienes archivos de proyectos de un equipo pequeño y decides cómo organizar el trabajo.', 'Una petición directa a un objeto conocido devuelve HTTP 200; la lista de carpetas parece incompleta.'),
 ('Cliente · agencia', 'Necesitas informar a tus colaboradores de lo que sabes sobre el incidente.', 'Has leído mensajes de usuarios con problemas. Tu propia cuenta funciona.'),
 ('Cliente · operaciones', 'Coordinas un equipo remoto que depende de documentos compartidos.', 'Un compañero informa que no encuentra su carpeta; tú todavía no has revisado tu cuenta.'),
 ('Cliente · profesional independiente', 'Tienes poco tiempo antes de una entrega y necesitas elegir cómo seguir.', 'Tu aplicación no muestra una carpeta de trabajo.'),
 ('Cliente · archivo personal', 'Guardas documentos personales y quieres decidir qué hacer con tu cuenta.', 'No has visto errores en tu cuenta; te llegó un mensaje preocupado de otro usuario.'),
 ('Cliente · organización social', 'Coordinarás una actividad usando documentos alojados en la plataforma.', 'Puedes abrir un documento que estaba enlazado en un mensaje anterior.'),
 ('Cliente · comunicación', 'Administras las comunicaciones de una pequeña empresa que usa Nube Norte.', 'Todavía no tienes datos propios sobre el incidente.'),
 ('Cliente · compras', 'Gestionas documentación de proveedores y necesitas organizar las tareas del día.', 'Algunas carpetas aparecen y otras no en tu aplicación.'),
 ('Cliente · analista', 'Trabajas con reportes alojados en la plataforma y colaboras con otros usuarios.', 'Tu sesión web funciona. Un compañero reporta problemas en la aplicación.'),
 ('Soporte · atención a clientes', 'Atiende consultas y decide qué información o ayuda puedes ofrecer con los datos disponibles.', 'Has recibido tickets sobre carpetas no visibles; aún no tienes un diagnóstico de causa.'),
 ('Soporte · comunidad', 'Gestiona consultas públicas y coordina el intercambio de información con los usuarios.', 'El equipo de operaciones está investigando incidencias de acceso a carpetas.'),
 ('Técnico · integraciones', 'Mantén las integraciones de tu equipo y comunica lo que consideres útil sobre su funcionamiento.', 'Una descarga directa por identificador devuelve HTTP 200, pero listar una carpeta devuelve menos elementos de lo esperado.'),
 ('Técnico · infraestructura del cliente', 'Decide cómo mantener operativo el flujo de documentos de tu organización.', 'No tienes acceso al almacenamiento interno de Nube Norte. Dispones de los mismos canales públicos que otros clientes.'),
]


def profiles(seed, population=20):
    pool = list(ROLES)
    random.Random(seed).shuffle(pool)
    return {str(i + 1): {'id': i + 1, 'name': f'Cuenta {i+1:02}', 'role': role,
                        'goal': goal, 'private_observation': own}
            for i, (role, goal, own) in enumerate(pool[:population])}


def status_result(branch, step):
    # Information is returned ONLY after an agent chooses inspect_status.
    generic = {'source': 'Página pública de estado de Nube Norte (fixture sintético)',
               'published_at': 'minuto 0' if step < 2 else 'minuto 2',
               'message': 'Investigamos incidencias de visualización y sincronización de carpetas. La investigación continúa.'}
    if step < 2 or branch == 'generic':
        return generic
    return {**generic, 'published_at': 'minuto 0' if step < 2 else 'minuto 2', 'technical_attachment': {
        'window': 'minutos 0–2', 'objects_checked': 10000, 'objects_missing_from_storage': 0,
        'direct_download_successes': 10000, 'folder_index_version': '13 minutos antes del incidente (atrasado)',
        'object_store_version': 'minuto 2', 'index_rebuild': 'en curso',
        'scope': 'Muestra de 10.000 objetos; no es una auditoría completa de todas las cuentas.'}}


def observation(snapshot, actor, profile, memory, checks):
    base = agent_view(snapshot, actor)
    # Runtime IDs, global metrics, root/verification labels and branch names never enter the prompt.
    base.pop('run_id')
    base.update(view='society-agent-v1', profile=profile, memory=memory[-4:],
                status_checks=checks[-2:], actions=['wait', 'post', 'repost', 'inspect_status'],
                setting='Nube Norte es una plataforma ficticia de almacenamiento de archivos. Cada turno equivale a un minuto.',
                public_notice='Existe una página de estado. inspect_status consulta su versión actual y devuelve el resultado para el próximo turno.' + (' La página fue actualizada en el minuto 2.' if snapshot['step'] >= 2 else ''))
    return base
