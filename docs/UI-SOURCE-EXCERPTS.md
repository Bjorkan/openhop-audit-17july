# UI source excerpts — fresh reverification

Only compiled frontend assets were supplied. These byte offsets identify evidence in the supplied snapshot; they are not recommended edit locations. Fixes must be made in the actual frontend source and the assets rebuilt.

## Duty-cycle display combines budget usage with configured limit

- Asset: `index-DULnzgZb.js`
- Byte offset: `50884`

```javascript
border text-[10px] font-semibold`,Ce.value])},d(_e.value.toUpperCase()),3)]),T(`div`,rn,[T(`span`,an,`OK: `+d(ye.value),1),T(`span`,on,`Drop: `+d(be.value),1),xe.value>0?(s(),E(`span`,sn,`Pen: `+d(xe.value),1)):b(``,!0)]),l(y).dutyCycleEnabled?(s(),E(`div`,cn,[T(`div`,ln,[r[6]||=T(`span`,null,`Duty Cycle`,-1),T(`span`,un,d(l(y).dutyCycleUtilization.toFixed(1))+`% / `+d(l(y).dutyCycleMax.toFixed(1))+`% `,1)]),T(`div`,dn,[T(`div`,{class:`h-full rounded-full transition-all duration-300`,style:m(Te.value)},null,4)])])):b(``,!0),x(qt)]),T(`div`,fn,[(s(),E(w,null,n(we,e=>T(`button`,{key:e.id,type:`button`,title:e.title,disabled:G.value,onClick:t=>se(e.id),class:g([`flex-1 py-2 text-xs fon
```

## Duty-cycle progress normalizes the already normalized value again

- Asset: `system-Ce1F4y5F.js`
- Byte offset: `998`

```javascript
} — Repeater`:`Repeater Dashboard`});let x=n(()=>{let e=s.value?.public_key;return!e||e===`Unknown`?`Unknown`:e.length>=16?`${e.slice(0,8)} ... ${e.slice(-8)}`:`${e}`}),S=n(()=>s.value!==null),C=n(()=>s.value?.version??`Unknown`),w=n(()=>s.value?.core_version??`Unknown`),T=n(()=>s.value?.noise_floor_dbm??null),E=n(()=>_.value>0?Math.min(g.value/_.value*100,100):0),D=n(()=>m.value===`no_tx`?{text:`No TX`,title:`No repeat, no local TX; adverts skipped`}:m.value===`monitor`?{text:`Monitor Mode`,title:`Monitoring only - not forwarding packets`}:h.value?{text:`Active`,title:`Forwarding with duty cycle enforcement`}:{text:`No Limits`,title:`Forwarding without duty cycle enforcement`}),O=n((
```

## API service returns Axios response.data, which is the backend envelope

- Asset: `api-sB-WuUnO.js`
- Byte offset: `99281`

```javascript
);if(wa())throw Na().handleAuthFailure(`expired`),Error(`Token expired`);return e}}static async getGeneratedRequestParams(){let e=await this.resolveRequestToken();return e?{headers:{Authorization:`Bearer ${e}`}}:{}}static async get(e,t,n){try{return(await $.get(e,{params:t,...n})).data}catch(e){throw this.handleError(e)}}static async post(e,t,n){try{return(await $.post(e,t,n)).data}catch(e){throw this.handleError(e)}}static async put(e,t,n){try{return(await $.put(e,t,n)).data}catch(e){throw this.handleError(e)}}static async delete(e,t){try{return(await $.delete(e,t)).data}catch(e){throw this.handleError(e)}}static async getTransportKeys(){try{let e=await this.getGeneratedRequestParams();return(await Q.tra
```

## Radio form reads the payload from the backend envelope

- Asset: `Configuration-gqXY-Aef.js`
- Byte offset: `9363`

```javascript
!1}={})=>{w.value=!0,T.value=null;try{if(W.value<-9||W.value>22)return T.value=`TX Power must be between -9 and +22 dBm for SX1262`,!1;let t={};L.value&&(t.frequency=L.value*1e6),z.value&&(t.spreading_factor=z.value),B.value&&(t.bandwidth=B.value*1e3),(W.value||W.value===0)&&(t.tx_power=W.value),G.value&&(t.coding_rate=G.value);let n=(await R.post(`/update_radio_config`,t)).data;if(n.message||n.persisted)return b.value=!1,F.value=!1,await u.fetchStats(),d.invalidate(`radioConfig`),e||(E.value=!0),!0;n.error?T.value=n.error:T.value=`Unknown response from server`}catch(e){console.error(`Failed to update radio settings:`,e),T.value=e.response?.data?.error||`Failed to update settings`}finally{w.value=!1}re
```

## Duty-cycle form reads the payload from the backend envelope

- Asset: `Configuration-gqXY-Aef.js`
- Byte offset: `56056`

```javascript
.value=6,g.value=r.value.enforcement_enabled!==!1,d.value=!0,p.value=``,m.value=``},w=()=>{d.value=!1,p.value=``,m.value=``},{showUnsavedModal:T,requestLeave:E,handleDiscard:O,handleSave:k,handleCancel:A}=pe(d,f,w,async()=>(await M(),!d.value));t({requestLeave:E,isEditing:d});let M=async()=>{f.value=!0,m.value=``,p.value=``;try{let e=(await R.post(`/update_duty_cycle_config`,{max_airtime_percent:h.value,enforcement_enabled:g.value})).data;e?.message||e?.persisted?(p.value=e?.message||`Settings saved successfully`,d.value=!1,await n.fetchStats(),setTimeout(()=>{p.value=``},3e3)):m.value=e?.error||`Failed to save settings`}catch(e){console.error(`Failed to save duty cycle settings:`,e),m.value=e.resp
```

## Advert form intentionally checks envelope success and envelope data

- Asset: `Configuration-gqXY-Aef.js`
- Byte offset: `131437`

```javascript
ds:V.value*60,penalty_enabled:H.value,violation_threshold:U.value,violation_decay_seconds:G.value*3600,base_penalty_seconds:K.value*3600,penalty_multiplier:te.value,max_penalty_seconds:q.value*3600,adaptive_enabled:ne.value,ewma_alpha:re.value,hysteresis_seconds:ie.value*60,quiet_max:J.value,normal_max:Y.value,busy_max:X.value},t=await R.post(`/update_advert_rate_limit_config`,e),n=t.data;t.success?(k.value=n?.message||`Settings saved successfully`,await s.fetchStats(),await Z(),await E(),Q(),T.value=!1,setTimeout(()=>{k.value=``},3e3)):(M.value=n?.error||`Failed to save settings`,console.error(`[AdvertSettings] Save failed:`,n?.error))}catch(e){console.error(`Failed to save advert settings:`,e),M.value=e.response?.data?.e
```

## Terminal fabricates persistence for quick controls

- Asset: `Terminal-CtqWeLbu.js`
- Byte offset: `547231`

```javascript
,this.writeLine(e,`  \x1B[36mforward\x1B[0m  - Forward packets`),this.writeLine(e,`  \x1B[36mmonitor\x1B[0m  - Monitor only (no forwarding)`),this.writeLine(e,`  \x1B[36mno_tx\x1B[0m    - No repeat, no local TX; adverts skipped`),n();return}t=await h.post(`/set_mode`,{mode:r},{timeout:3e4}),t.data&&(t.data.applied=[`mode=${r}`],t.data.persisted=!0,t.data.live_update=!0);break}case`duty`:{let r=i.toLowerCase();if(r!==`on`&&r!==`off`){a(),this.writeError(e,`Duty cycle must be "on" or "off"`),this.writeLine(e,``),this.writeInfo(e,`Valid values:`),this.writeLine(e,`  \x1B[36mon\x1B[0m   - Enable duty cycle enforcement`),this.writeLine(e,`  \x1B[36moff\x1B[0m  - Disable duty cycle enforcement`),n(
```
