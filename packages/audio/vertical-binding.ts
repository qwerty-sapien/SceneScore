/** Preserve Python's exact number/string tokens while projecting canonical musical data. */
type Value={raw?:string;array?:Value[];object?:[string,Value][]};
export function musicalInputBytes(payload:string){
 if(payload.length>32*1024*1024)throw Error('Musical binding byte budget');
 const parsed=JSON.parse(payload) as {resolved_time_s:number;id:string}[];
 if(!Array.isArray(parsed)||parsed.length>5000)throw Error('Musical binding event budget');
 let at=0;
 const whitespace=()=>{while(/\s/.test(payload[at]??'')&&at<payload.length)at++;};
 const quoted=()=>{const start=at++;while(at<payload.length){const c=payload[at++];if(c==='\\')at++;else if(c==='"')return payload.slice(start,at);}throw Error('Unterminated JSON string');};
 function read(depth=0):Value{
  if(depth>24)throw Error('Musical binding nesting budget');whitespace();const start=at,c=payload[at++];
  if(c==='['){const array:Value[]=[];whitespace();if(payload[at]===']'){at++;return {array};}
   while(true){array.push(read(depth+1));whitespace();if(payload[at++ ]===']')break;}return {array};}
  if(c==='{'){const object:[string,Value][]=[];whitespace();if(payload[at]==='}'){at++;return {object};}
   while(true){whitespace();const key=JSON.parse(quoted()) as string;whitespace();at++;object.push([key,read(depth+1)]);whitespace();if(payload[at++ ]==='}')break;}return {object};}
  at=start;if(c==='"')return {raw:quoted()};
  while(at<payload.length&&!/[\s,\]}]/.test(payload[at]))at++;
  return {raw:payload.slice(start,at)};
 }
 const root=read();
 function encoded(value:Value):string{
  if(value.array)return '['+value.array.map(encoded).join(',')+']';
  if(value.object)return '{'+[...value.object].sort(([a],[b])=>a<b?-1:a>b?1:0).map(([key,v])=>JSON.stringify(key)+':'+encoded(v)).join(',')+'}';
  return value.raw!;
 }
 const values=root.array!;
 if(values.length!==parsed.length||values.some(v=>!v.object))throw Error('Invalid musical binding array');
 const order=parsed.map((event,index)=>({event,index})).sort((a,b)=>a.event.resolved_time_s-b.event.resolved_time_s||(a.event.id<b.event.id?-1:a.event.id>b.event.id?1:0));
 return new TextEncoder().encode('['+order.map(({index})=>encoded({object:values[index].object!.filter(([key])=>key!=='plan_id'&&key!=='provenance')})).join(',')+']\n');
}
