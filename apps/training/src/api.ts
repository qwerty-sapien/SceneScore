import type {AutomaticStatus,DiagnosticsReport,MarkerRequest,ModelSummary,Review,ReviewBundle,Role,Source,Status,Trace} from './types';
export const API_ROOT='http://127.0.0.1:8767/v1';
export class TrainingAPI {
 private session:string|null=null;
 constructor(private readonly fetcher:typeof fetch=globalThis.fetch.bind(globalThis),private readonly root=API_ROOT){}
 private async response(path:string,body?:unknown,startupToken?:string,signal?:AbortSignal){
  const token=startupToken??this.session;if(!token)throw Error('Connect the local training service first.');
  const requestBody=body===undefined?undefined:JSON.stringify(body);
  if(requestBody!==undefined&&new TextEncoder().encode(requestBody).length>16384)throw Error('Request exceeds the local service limit.');
  const response=await this.fetcher(this.root+path,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,...(body===undefined?{}:{'Content-Type':'application/json'})},body:requestBody,cache:'no-store',credentials:'omit',redirect:'error',signal:signal??AbortSignal.timeout(path==='/train'?60000:6000)});
  if(!response.ok){let message='Local service request failed ('+response.status+').';try{const error=await response.json();if(typeof error.error==='string')message=error.error;}catch{/* bounded server may omit error body */}throw Error(message);}
  return response;
 }
 private async json<T>(path:string,body?:unknown,signal?:AbortSignal):Promise<T>{return (await this.response(path,body,undefined,signal)).json();}
 async authenticate(token:string):Promise<Status>{const trimmed=token.trim();if(trimmed.length<16||trimmed.length>256||/\s/.test(trimmed))throw Error('Paste the token printed by the local training service.');const result=await(await this.response('/session',{},trimmed)).json();if(typeof result.session!=='string')throw Error('Invalid local session response.');this.session=result.session;return result.status;}
 status(signal?:AbortSignal){return this.json<Status>('/status',undefined,signal);}
 automaticStatus(signal?:AbortSignal){return this.json<AutomaticStatus>('/automatic/status',undefined,signal);}
 connectAutomatic(){return this.json<AutomaticStatus>('/automatic/connect',{consent:true});}
 startAutomatic(){return this.json<AutomaticStatus>('/automatic/start',{consent:true});}
 stopAutomatic(){return this.json<AutomaticStatus>('/automatic/stop',{});}
 labelAutomatic(value:{id:string;client_ms:number;run_id:string}){return this.json<{saved:true;label_id:string;status:AutomaticStatus}>('/automatic/label',value);}
 diagnostics(signal?:AbortSignal){return this.json<DiagnosticsReport>('/diagnostics',undefined,signal);}
 monitorDiagnostics(enabled:boolean){return this.json<DiagnosticsReport>('/diagnostics/monitor',{enabled});}
 checkDiagnostics(request_bluetooth_permission=false){return this.json<DiagnosticsReport>('/diagnostics/check',{request_bluetooth_permission});}
 sources(){return this.json<{sources:Source[];blockers:string[]}>('/sources');}
 connect(source_id:string,device_model:string){return this.json<Status>('/connect',{source_id,device_model,consent:true});}
 disconnect(){return this.json<Status>('/disconnect',{});}
 trace(signal?:AbortSignal){return this.json<Trace>('/trace',undefined,signal);}
 startRecord(value:{participant_id:string;refit_id:string;role:Role;consent_statement:string;seconds:number;metadata_confirmed:boolean}){return this.json<Status>('/record/start',{...value,consent:true});}
 stopRecord(){return this.json<Status>('/record/stop',{});}
 marker(value:MarkerRequest){return this.json<unknown>('/marker',value);}
 review(sessionId:string){return this.json<ReviewBundle>('/review?session_id='+encodeURIComponent(sessionId));}
 segment(sessionId:string,start:number,end:number){return this.json<Trace>('/segment?session_id='+encodeURIComponent(sessionId)+'&start_s='+start+'&end_s='+end);}
 saveReview(sessionId:string,review:Review){return this.json<Review>('/review',{session_id:sessionId,...review});}
 train(){return this.json<{model:ModelSummary;report:unknown}>('/train',{});}
 deleteSession(sessionId:string,confirmed:string){return this.json<Status>('/delete',{session_id:sessionId,confirmed_session_id:confirmed});}
 async download(sessionId?:string){const response=await this.response(sessionId?'/export?session_id='+encodeURIComponent(sessionId):'/model');const length=Number(response.headers.get('Content-Length')??0);if(length>32*1024*1024)throw Error('Local export exceeds 32 MiB.');const blob=await response.blob();if(blob.size>32*1024*1024)throw Error('Local export exceeds 32 MiB.');return blob;}
 close(){this.session=null;}
}
export function consumeTokenFragment(location:{hash:string;pathname:string;search:string},history:{state:unknown;replaceState:(data:unknown,unused:string,url:string)=>void}):string{
 const params=new URLSearchParams(location.hash.replace(/^#/,''));const token=params.get('token')??'';
 if(params.has('token')){params.delete('token');const rest=params.toString();history.replaceState(history.state,'',location.pathname+location.search+(rest?'#'+rest:''));}
 return token;
}
