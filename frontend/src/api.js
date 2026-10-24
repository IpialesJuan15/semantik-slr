export async function api(path, options={}) {
  const init={...options};
  if(init.body && !(init.body instanceof FormData)){init.headers={'Content-Type':'application/json',...init.headers};init.body=JSON.stringify(init.body)}
  let response;
  try{response=await fetch(`/api${path}`,init)}catch{throw new Error('No se pudo conectar con el servidor. Comprueba que siga ejecutándose.')}
  if(!response.ok){
    const data=await response.json().catch(()=>({}));
    if(Array.isArray(data.detail)) throw new Error(data.detail.map(e=>`${e.loc.at(-1)}: ${e.msg}`).join('; '));
    const error=new Error(typeof data.detail==='string'?data.detail:data.detail?.message||`La operación falló (${response.status}). Vuelve a intentarlo.`);error.status=response.status;error.retryAfter=data.detail?.retry_after_seconds;throw error
  }
  return response.json();
}
export const labels={pending:'Pendiente',included:'Incluido',excluded:'Excluido'};
export function date(value){return new Date(value).toLocaleString('es-EC')}
