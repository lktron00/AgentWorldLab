"""Predeclared synthetic cases. Truth belongs to the evaluator, never the model prompt."""
import random
from .observations import agent_view

CASES = [
 {'id':'cloud-index','domain':'cloud','title':'Carpetas ocultas por un índice atrasado','truth':False,
  'setting':'Nube Norte es una plataforma ficticia de almacenamiento de archivos.',
  'question':'¿Se han perdido permanentemente archivos de clientes durante este incidente?',
  'post':'No encuentro varias carpetas de Nube Norte. ¿Se habrán perdido los archivos? Otros compañeros reportan lo mismo.',
  'generic':'Se investigan problemas de acceso y sincronización de carpetas.',
  'diagnosis':{'observed_window':'minutos 0–2','sample_objects':10000,'missing_objects':0,'direct_downloads_ok':10000,'folder_index':'13 minutos atrasado','scope':'Muestra de objetos consultables, no auditoría completa de todas las cuentas.'},
  'record':{'object_id':'doc-own-17','direct_get':'HTTP 200','folder_listing':'el objeto no aparece','last_delete_event':None},
  'hint':'La lista de carpetas no coincide con lo que esperabas; aún no has comprobado el objeto directamente.','quality':'relevant_sample'},
 {'id':'cloud-deletion','domain':'cloud','title':'Borrado real sin copia recuperable','truth':True,
  'setting':'Nube Norte es una plataforma ficticia de almacenamiento de archivos.',
  'question':'¿Se han perdido permanentemente archivos de clientes durante este incidente?',
  'post':'Faltan carpetas y el enlace directo que guardé devuelve un error. Me preocupa que Nube Norte haya perdido archivos.',
  'generic':'Se investigan problemas de acceso y sincronización de carpetas.',
  'diagnosis':{'observed_window':'minutos 0–2','sample_objects':10000,'missing_objects':37,'deleted_object_versions':37,'replica_results':'los mismos 37 objetos ausentes en las tres réplicas','restore_job':'terminó: sin versiones recuperables para esos 37 IDs','scope':'Resultado de esos 37 IDs, no de todas las cuentas.'},
  'record':{'object_id':'doc-own-17','direct_get':'HTTP 404','deletion_event':'delete propagado a tres réplicas','restore_result':'sin versión recuperable'},
  'hint':'Falta una carpeta; un enlace directo que usabas ya no abre.','quality':'convergent_evidence'},
 {'id':'cloud-stale','domain':'cloud','title':'Un reporte antiguo tranquiliza durante un borrado real','truth':True,
  'setting':'Nube Norte es una plataforma ficticia de almacenamiento de archivos.',
  'question':'¿Se han perdido permanentemente archivos de clientes durante este incidente?',
  'post':'Desde hace unos minutos faltan documentos de Nube Norte. No sé si se borraron o si es un problema de la aplicación.',
  'generic':'Se investigan problemas de acceso y sincronización de carpetas.',
  'diagnosis':{'report_generated':'20 minutos ANTES del incidente','sample_objects':10000,'missing_objects':0,'direct_downloads_ok':10000,'scope':'Muestra previa al inicio de los fallos; no incluye comprobaciones posteriores.'},
  'record':{'object_id':'doc-own-17','checked_at':'minuto actual del incidente','direct_get':'HTTP 404','deletion_event':'delete posterior a la muestra pública','restore_result':'sin versión recuperable'},
  'hint':'Tu carpeta dejó de aparecer después de la hora del reporte de mantenimiento anterior.','quality':'stale_reassurance'},
 {'id':'billing-hold','domain':'billing','title':'Una autorización parece un segundo cobro','truth':False,
  'setting':'Mercado Sur es una tienda ficticia con pagos de tarjeta simulados.',
  'question':'¿Se liquidaron dos cobros definitivos por el mismo pedido durante este incidente?',
  'post':'Mi banco muestra dos movimientos de Mercado Sur por un solo pedido. ¿Nos están cobrando dos veces?',
  'generic':'Se investigan consultas sobre movimientos duplicados en el historial de pagos.',
  'diagnosis':{'order_sample':'200 pedidos','events_per_order':[{'type':'AUTHORIZATION','state':'PENDING'},{'type':'CAPTURE','state':'SETTLED'}],'settled_captures_per_order':1,'scope':'Una autorización pendiente no equivale por sí sola a un segundo cobro liquidado.'},
  'record':{'order_id':'own-order-17','events':[{'id':'auth-17','type':'AUTHORIZATION','state':'PENDING'},{'id':'cap-17','type':'CAPTURE','state':'SETTLED'}],'total_settled_captures':1},
  'hint':'Ves dos movimientos por un pedido; todavía no abriste el detalle de sus estados.','quality':'disambiguating_records'},
 {'id':'billing-double','domain':'billing','title':'Dos cobros definitivos del mismo pedido','truth':True,
  'setting':'Mercado Sur es una tienda ficticia con pagos de tarjeta simulados.',
  'question':'¿Se liquidaron dos cobros definitivos por el mismo pedido durante este incidente?',
  'post':'Veo dos movimientos con el mismo importe para mi pedido de Mercado Sur. ¿Hay un problema de cobros duplicados?',
  'generic':'Se investigan consultas sobre movimientos duplicados en el historial de pagos.',
  'diagnosis':{'order_sample':'200 pedidos','affected_orders':12,'example_order':'sample-order-8','events':[{'id':'cap-A','type':'CAPTURE','state':'SETTLED','amount':40},{'id':'cap-B','type':'CAPTURE','state':'SETTLED','amount':40}],'same_order_id':True,'scope':'Dos IDs de liquidación distintos asociados a un pedido, sin anulación registrada.'},
  'record':{'order_id':'own-order-17','events':[{'id':'cap-own-A','type':'CAPTURE','state':'SETTLED','amount':40},{'id':'cap-own-B','type':'CAPTURE','state':'SETTLED','amount':40}],'reversal':None},
  'hint':'Dos movimientos muestran el mismo importe; no conoces aún sus identificadores ni su estado final.','quality':'convergent_evidence'},
 {'id':'billing-small-sample','domain':'billing','title':'Una muestra mínima no resuelve la alarma de cobros','truth':False,
  'setting':'Mercado Sur es una tienda ficticia con pagos de tarjeta simulados.',
  'question':'¿Se liquidaron dos cobros definitivos por el mismo pedido durante este incidente?',
  'post':'Algunas personas ven dos movimientos por pedido en Mercado Sur. No sabemos cuántas cuentas están afectadas.',
  'generic':'Se investigan consultas sobre movimientos duplicados en el historial de pagos.',
  'diagnosis':{'sample_orders':2,'selection':'primeros dos pedidos disponibles de una sola sucursal','settled_captures_per_order':[1,1],'scope':'La muestra no incluye el resto de sucursales ni todos los pedidos reportados.'},
  'record':{'order_id':'own-order-17','events':[{'id':'auth-17','type':'AUTHORIZATION','state':'PENDING'},{'id':'cap-17','type':'CAPTURE','state':'SETTLED'}],'total_settled_captures':1,'scope':'Solo tu pedido; no permite inspeccionar pedidos de otras cuentas.'},
  'hint':'Tu historial muestra dos movimientos, pero los comentarios públicos se refieren a otras sucursales.','quality':'limited_sample'},
 {'id':'security-false-positive','domain':'security','title':'Una alerta del escáner con artefacto íntegro','truth':False,
  'setting':'Paquete Faro es una dependencia de software ficticia usada por equipos de trabajo.',
  'question':'¿El artefacto distribuido durante este incidente fue modificado sin autorización?',
  'post':'El escáner marcó una alerta sobre Paquete Faro. ¿La versión que instalamos pudo haber sido alterada?',
  'generic':'Se investiga una alerta del escáner para la distribución reciente del paquete.',
  'diagnosis':{'version':'2.4.1','downloaded_digest':'sha256:fixture-approved-A','signed_manifest_digest':'sha256:fixture-approved-A','signature_check':'válida','scanner_rule':'coincidencia por nombre de archivo','scope':'Comprobación del artefacto 2.4.1, no de cualquier versión o descarga futura.'},
  'record':{'installed_version':'2.4.1','local_digest':'sha256:fixture-approved-A','signed_manifest_digest':'sha256:fixture-approved-A','signature_check':'válida'},
  'hint':'Un escáner emitió una alerta; todavía no comparaste el hash local con el manifiesto de la versión.','quality':'matching_integrity_records'},
 {'id':'security-modified','domain':'security','title':'El paquete descargado no coincide con el manifiesto firmado','truth':True,
  'setting':'Paquete Faro es una dependencia de software ficticia usada por equipos de trabajo.',
  'question':'¿El artefacto distribuido durante este incidente fue modificado sin autorización?',
  'post':'Varios equipos recibieron una alerta sobre Paquete Faro. Necesitamos entender qué versión se descargó realmente.',
  'generic':'Se investiga una alerta del escáner para la distribución reciente del paquete.',
  'diagnosis':{'version':'2.4.1','downloaded_digest':'sha256:fixture-unknown-B','signed_manifest_digest':'sha256:fixture-approved-A','signature_check':'inválida para el artefacto descargado','authorized_release_changes':[],'scope':'La diferencia afecta al artefacto servido durante el incidente, no demuestra qué hizo al ejecutarse.'},
  'record':{'installed_version':'2.4.1','local_digest':'sha256:fixture-unknown-B','signed_manifest_digest':'sha256:fixture-approved-A','signature_check':'inválida','authorized_change_ticket':None},
  'hint':'Tu equipo instaló la versión reciente. No has inspeccionado aún sus datos de integridad.','quality':'integrity_mismatch'},
 {'id':'security-wrong-version','domain':'security','title':'Una auditoría de otra versión contradice la alerta actual','truth':True,
  'setting':'Paquete Faro es una dependencia de software ficticia usada por equipos de trabajo.',
  'question':'¿El artefacto distribuido durante este incidente fue modificado sin autorización?',
  'post':'La alerta sobre Paquete Faro parece afectar a la actualización de hoy; algunos comparten una auditoría anterior que decía que todo estaba bien.',
  'generic':'Se investiga una alerta del escáner para la distribución reciente del paquete.',
  'diagnosis':{'audited_version':'2.4.0','current_distribution_version':'2.4.1','audited_digest':'sha256:fixture-old-approved','signature_check_for_2_4_0':'válida','scope':'Esta auditoría corresponde a 2.4.0. No contiene una comprobación de 2.4.1.'},
  'record':{'installed_version':'2.4.1','local_digest':'sha256:fixture-unknown-B','signed_manifest_digest_for_2_4_1':'sha256:fixture-approved-A','signature_check':'inválida','authorized_change_ticket':None},
  'hint':'Instalaste 2.4.1, pero el mensaje tranquilizador que circula menciona una revisión previa.','quality':'wrong_version_reassurance'},
]
BY_ID = {c['id']:c for c in CASES}


def profiles(case, seed):
    domains={'cloud':('archivos','colaboradores'),'billing':('pedidos y pagos','clientes y compañeros'),'security':('dependencias de software','equipo técnico')}
    subject,peers=domains[case['domain']]
    roles=[f'Usuario · equipo {i+1:02}' for i in range(16)]+['Soporte · consultas privadas','Soporte · comunidad','Técnico · integraciones','Técnico · operaciones']
    random.Random(seed).shuffle(roles)
    return {str(i+1):{'id':i+1,'name':f'Cuenta {i+1:02}','role':role,
            'goal':f'Organiza tu trabajo con {subject} y decide cómo coordinarte con {peers}.',
            'private_observation':case['hint'] if i%4!=3 else 'Tu equipo no ha confirmado una incidencia propia. Recibes consultas de otros usuarios.'}
            for i,role in enumerate(roles)}


def tool_result(case, branch, tool, step, actor):
    if tool=='inspect_record':
        return {'id':f'private-record-{actor}-{step}','source':'Registro privado de TU cuenta (fixture sintético)',
                'scope':'No concede acceso a otras cuentas.', 'record':case['record'] if actor%4!=0 else {'local_check':'sin anomalía propia observada','scope':'solo los elementos locales revisados'}}
    result={'id':f'public-status-{step}','source':'Página pública del servicio (fixture sintético)','message':case['generic'],'updated_at_step':2 if step>=2 else 0}
    if branch=='diagnostic' and step>=2:result['attachment']=case['diagnosis']
    return result


def view(case,snapshot,actor,profile,memory,checks):
    result=agent_view(snapshot,actor);result.pop('run_id')
    result.update(view='study-agent-v1',setting=case['setting'],question=case['question'],profile=profile,
                  memory=memory[-5:],checks=checks[-4:],actions=['wait','post','repost','inspect_status','inspect_record'],
                  public_notice='Puedes consultar la página pública o el registro privado de TU cuenta. Cada consulta consume un turno y su respuesta llega en el siguiente.'+(' La página pública fue actualizada en el minuto 2.' if snapshot['step']>=2 else ''))
    return result
